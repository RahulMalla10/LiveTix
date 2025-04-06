from rest_framework import serializers
from .models import Concert, Booking

class ConcertSerializer(serializers.ModelSerializer):
    class Meta:
        model = Concert
        fields = ['id', 'title', 'artist', 'date', 'venue', 'ticket_price', 'available_tickets']

class BookingSerializer(serializers.ModelSerializer):
    concert = ConcertSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'concert', 'user', 'booked_at']