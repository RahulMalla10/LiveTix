import logging
import os
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Concert, Booking
from .serializers import ConcertSerializer, BookingSerializer
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import io
import qrcode

# Set up logging
logger = logging.getLogger(__name__)

@api_view(['GET'])
def concert_list(request):
    concerts = Concert.objects.all()
    serializer = ConcertSerializer(concerts, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def book_ticket(request, concert_id):
    logger.info(f"Starting book_ticket for concert ID {concert_id}")
    try:
        data = json.loads(request.body)
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            logger.warning("Name or email missing in request")
            return Response({'error': 'Name and email are required'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            concert = get_object_or_404(Concert, id=concert_id)
            if concert.available_tickets <= 0:
                logger.warning(f"No tickets available for concert ID {concert_id}")
                return Response({'error': 'No tickets available'}, status=status.HTTP_400_BAD_REQUEST)

            # Create a booking associated with the authenticated user
            logger.info(f"Creating booking for user {request.user.username}")
            booking = Booking.objects.create(
                concert=concert,
                user=request.user,
                name=name,
                email=email
            )
            concert.available_tickets -= 1
            concert.save()
            logger.info(f"Updated available tickets for concert ID {concert_id}: {concert.available_tickets}")

            # Generate PDF ticket
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="ticket-{concert_id}.pdf"'

            # Define a custom SimpleDocTemplate with background and margins
            def draw_page_background(canvas, doc):
                width, height = letter
                logger.info("Drawing page background")
                try:
                    canvas.saveState()
                    # Dark gradient background
                    canvas.setFillColor(colors.Color(0.05, 0.05, 0.2))  # Very dark blue
                    canvas.rect(0, 0, width, height, fill=1, stroke=0)
                    canvas.setFillColor(colors.Color(0.2, 0.2, 0.5, alpha=0.5))  # Lighter blue gradient
                    canvas.rect(0, height * 0.3, width, height * 0.7, fill=1, stroke=0)

                    # Subtle decorative line
                    canvas.setStrokeColor(colors.Color(0.8, 0.8, 1, alpha=0.3))
                    canvas.setLineWidth(1)
                    canvas.line(inch, height - 0.5 * inch, width - inch, height - 0.5 * inch)

                    canvas.restoreState()
                    logger.info("Background drawn successfully")
                except Exception as e:
                    logger.error(f"Error in draw_page_background: {str(e)}")
                    raise

            # Set page margins to ensure content fits
            doc = SimpleDocTemplate(
                response,
                pagesize=letter,
                leftMargin=inch,
                rightMargin=inch,
                topMargin=inch,
                bottomMargin=inch
            )

            elements = []

            # Define styles for text
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'Title',
                fontName='Helvetica-Bold',
                fontSize=24,
                textColor=colors.white,
                spaceAfter=10,
                alignment=1,  # Center alignment
            )
            label_style = ParagraphStyle(
                'Label',
                fontName='Helvetica-Bold',
                fontSize=11,
                textColor=colors.black,
                spaceAfter=4,
            )
            value_style = ParagraphStyle(
                'Value',
                fontName='Helvetica',
                fontSize=11,
                textColor=colors.black,
                spaceAfter=4,
            )
            small_text_style = ParagraphStyle(
                'SmallText',
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.black,
                spaceAfter=8,
                alignment=1,  # Center alignment
            )
            bold_text_style = ParagraphStyle(
                'BoldText',
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=colors.black,
                spaceAfter=8,
                alignment=1,  # Center alignment
            )

            # Add ticket content
            logger.info("Adding PDF elements")

            # Header: Logo and Title
            logo_path = os.path.expanduser("~/Desktop/projects/livetix/static/LT.png")
            try:
                if not os.path.exists(logo_path):
                    raise FileNotFoundError(f"Logo file not found at {logo_path}")
                logo = Image(logo_path, width=80, height=40)  # Adjust dimensions as needed
                logo.hAlign = 'CENTER'
                elements.append(logo)
            except Exception as e:
                logger.warning(f"Could not load logo: {str(e)}")
                elements.append(Paragraph("(Logo Placeholder)", small_text_style))
            elements.append(Spacer(1, 0.2 * inch))
            elements.append(Paragraph("LiveTix Concert Ticket", title_style))
            elements.append(Spacer(1, 0.3 * inch))

            # Content Card: Concert and Booker Details, QR Code
            content = []

            # Concert and Booker Details
            details_data = [
                [Paragraph("Concert", label_style), Paragraph(concert.title, value_style)],
                [Paragraph("Artist", label_style), Paragraph(concert.artist, value_style)],
                [Paragraph("Date", label_style), Paragraph(concert.date.strftime('%Y-%m-%d %H:%M'), value_style)],
                [Paragraph("Venue", label_style), Paragraph(concert.venue, value_style)],
                [Paragraph("Price", label_style), Paragraph(f"${concert.ticket_price:.2f}", value_style)],
                [Paragraph("Booked By", label_style), Paragraph(name, value_style)],
                [Paragraph("Email", label_style), Paragraph(email, value_style)],
            ]
            details_table = Table(details_data, colWidths=[1.2 * inch, 2.3 * inch])
            details_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, -1), 10),
                ('RIGHTPADDING', (1, 0), (1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ]))
            content.append(details_table)
            content.append(Spacer(1, 0.3 * inch))

            # QR Code
            logger.info("Generating QR code")
            qr_data = f"Ticket ID: {booking.id} | Concert: {concert.title}"
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=8,
                border=2,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            qr_img.save(buffer, format="PNG")
            buffer.seek(0)

            content.append(Paragraph("Scan to Verify", bold_text_style))
            content.append(Spacer(1, 0.1 * inch))
            qr_image = Image(buffer, width=100, height=100)
            qr_table = Table([[qr_image]], colWidths=[100])
            qr_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            content.append(qr_table)
            content.append(Spacer(1, 0.3 * inch))

            # Thank You Message
            content.append(Paragraph("Thank you for choosing LiveTix!", small_text_style))

            # Wrap content in a card-like background
            content_table = Table([[content]], colWidths=[4.5 * inch])
            content_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.9)),  # Semi-transparent white
                ('BOX', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),  # Subtle gray border
                ('ROUND', (0, 0), (-1, -1), 10),  # Rounded corners
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 20),
                ('TOPPADDING', (0, 0), (-1, -1), 20),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
            ]))
            elements.append(content_table)

            # Log the elements list for debugging
            logger.info(f"Elements list: {[str(e) for e in elements]}")

            # Build the PDF with onFirstPage and onLaterPages
            logger.info("Building PDF with elements")
            doc.build(elements, onFirstPage=draw_page_background, onLaterPages=draw_page_background)
            logger.info("PDF built successfully")

            return response

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in book_ticket: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def register(request):
    logger.info("Starting register")
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not username or not email or not password:
            logger.warning("Username, email, or password missing in request")
            return Response({'error': 'Username, email, and password are required'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            logger.warning(f"Username {username} already exists")
            return Response({'error': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            logger.warning(f"Email {email} already exists")
            return Response({'error': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        logger.info(f"User {username} created successfully")

        # Generate token for the new user
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

    except json.JSONDecodeError:
        logger.error("Invalid JSON in request")
        return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error in register: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user)
    serializer = BookingSerializer(bookings, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def download_ticket(request, booking_id):
    logger.info(f"Starting download_ticket for booking ID {booking_id}")
    try:
        # Fetch the booking and ensure it belongs to the authenticated user
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        concert = booking.concert
        name = booking.name
        email = booking.email

        # Generate PDF ticket
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket-{concert.id}.pdf"'

        # Define a custom SimpleDocTemplate with background and margins
        def draw_page_background(canvas, doc):
            width, height = letter
            logger.info("Drawing page background")
            try:
                canvas.saveState()
                # Dark gradient background
                canvas.setFillColor(colors.Color(0.05, 0.05, 0.2))  # Very dark blue
                canvas.rect(0, 0, width, height, fill=1, stroke=0)
                canvas.setFillColor(colors.Color(0.2, 0.2, 0.5, alpha=0.5))  # Lighter blue gradient
                canvas.rect(0, height * 0.3, width, height * 0.7, fill=1, stroke=0)

                # Subtle decorative line
                canvas.setStrokeColor(colors.Color(0.8, 0.8, 1, alpha=0.3))
                canvas.setLineWidth(1)
                canvas.line(inch, height - 0.5 * inch, width - inch, height - 0.5 * inch)

                canvas.restoreState()
                logger.info("Background drawn successfully")
            except Exception as e:
                logger.error(f"Error in draw_page_background: {str(e)}")
                raise

        # Set page margins to ensure content fits
        doc = SimpleDocTemplate(
            response,
            pagesize=letter,
            leftMargin=inch,
            rightMargin=inch,
            topMargin=inch,
            bottomMargin=inch
        )

        elements = []

        # Define styles for text
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=colors.white,
            spaceAfter=10,
            alignment=1,  # Center alignment
        )
        label_style = ParagraphStyle(
            'Label',
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=colors.black,
            spaceAfter=4,
        )
        value_style = ParagraphStyle(
            'Value',
            fontName='Helvetica',
            fontSize=11,
            textColor=colors.black,
            spaceAfter=4,
        )
        small_text_style = ParagraphStyle(
            'SmallText',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=8,
            alignment=1,  # Center alignment
        )
        bold_text_style = ParagraphStyle(
            'BoldText',
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.black,
            spaceAfter=8,
            alignment=1,  # Center alignment
        )

        # Add ticket content
        logger.info("Adding PDF elements")

        # Header: Logo and Title
        logo_path = os.path.expanduser("~/Desktop/projects/livetix/static/LT.png")
        try:
            if not os.path.exists(logo_path):
                raise FileNotFoundError(f"Logo file not found at {logo_path}")
            logo = Image(logo_path, width=80, height=40)  # Adjust dimensions as needed
            logo.hAlign = 'CENTER'
            elements.append(logo)
        except Exception as e:
            logger.warning(f"Could not load logo: {str(e)}")
            elements.append(Paragraph("(Logo Placeholder)", small_text_style))
        elements.append(Spacer(1, 0.2 * inch))
        elements.append(Paragraph("LiveTix Concert Ticket", title_style))
        elements.append(Spacer(1, 0.3 * inch))

        # Content Card: Concert and Booker Details, QR Code
        content = []

        # Concert and Booker Details
        details_data = [
            [Paragraph("Concert", label_style), Paragraph(concert.title, value_style)],
            [Paragraph("Artist", label_style), Paragraph(concert.artist, value_style)],
            [Paragraph("Date", label_style), Paragraph(concert.date.strftime('%Y-%m-%d %H:%M'), value_style)],
            [Paragraph("Venue", label_style), Paragraph(concert.venue, value_style)],
            [Paragraph("Price", label_style), Paragraph(f"${concert.ticket_price:.2f}", value_style)],
            [Paragraph("Booked By", label_style), Paragraph(name, value_style)],
            [Paragraph("Email", label_style), Paragraph(email, value_style)],
        ]
        details_table = Table(details_data, colWidths=[1.2 * inch, 2.3 * inch])
        details_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (0, -1), 10),
            ('RIGHTPADDING', (1, 0), (1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        content.append(details_table)
        content.append(Spacer(1, 0.3 * inch))

        # QR Code
        logger.info("Generating QR code")
        qr_data = f"Ticket ID: {booking.id} | Concert: {concert.title}"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=8,
            border=2,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        content.append(Paragraph("Scan to Verify", bold_text_style))
        content.append(Spacer(1, 0.1 * inch))
        qr_image = Image(buffer, width=100, height=100)
        qr_table = Table([[qr_image]], colWidths=[100])
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        content.append(qr_table)
        content.append(Spacer(1, 0.3 * inch))

        # Thank You Message
        content.append(Paragraph("Thank you for choosing LiveTix!", small_text_style))

        # Wrap content in a card-like background
        content_table = Table([[content]], colWidths=[4.5 * inch])
        content_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 1, 1, alpha=0.9)),  # Semi-transparent white
            ('BOX', (0, 0), (-1, -1), 0.5, colors.Color(0.7, 0.7, 0.7)),  # Subtle gray border
            ('ROUND', (0, 0), (-1, -1), 10),  # Rounded corners
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 20),
            ('RIGHTPADDING', (0, 0), (-1, -1), 20),
            ('TOPPADDING', (0, 0), (-1, -1), 20),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ]))
        elements.append(content_table)

        # Log the elements list for debugging
        logger.info(f"Elements list: {[str(e) for e in elements]}")

        # Build the PDF with onFirstPage and onLaterPages
        logger.info("Building PDF with elements")
        doc.build(elements, onFirstPage=draw_page_background, onLaterPages=draw_page_background)
        logger.info("PDF built successfully")

        return response

    except Exception as e:
        logger.error(f"Error in download_ticket: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    logger.info(f"Starting cancel_booking for booking ID {booking_id}")
    try:
        with transaction.atomic():
            # Fetch the booking and ensure it belongs to the authenticated user
            booking = get_object_or_404(Booking, id=booking_id, user=request.user)
            concert = booking.concert

            # Increment the available tickets for the concert
            concert.available_tickets += 1
            concert.save()
            logger.info(f"Incremented available tickets for concert ID {concert.id}: {concert.available_tickets}")

            # Delete the booking
            booking.delete()
            logger.info(f"Booking ID {booking_id} canceled successfully")

            return Response({'message': 'Booking canceled successfully'}, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Error in cancel_booking: {str(e)}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)