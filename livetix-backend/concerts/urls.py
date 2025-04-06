from django.urls import path
from . import views

urlpatterns = [
    path('concerts/', views.concert_list, name='concert_list'),
    path('concerts/<int:concert_id>/book/', views.book_ticket, name='book_ticket'),
    path('register/', views.register, name='register'),
    path('booking-history/', views.booking_history, name='booking_history'),
    path('bookings/<int:booking_id>/download/', views.download_ticket, name='download_ticket'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel_booking'),  # New endpoint
]