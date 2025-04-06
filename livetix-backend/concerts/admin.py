from django.contrib import admin
from .models import Concert, Booking

@admin.register(Concert)
class ConcertAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'artist', 'date', 'venue']  # Removed 'artist_image'
    list_filter = ['date']
    search_fields = ['title', 'artist']

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'concert', 'user', 'booked_at']
    list_filter = ['booked_at']
    search_fields = ['user__username']