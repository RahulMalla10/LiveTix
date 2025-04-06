from django.apps import AppConfig

class ConcertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'  # Ensures BigAutoField is used for model IDs by default
    name = 'concerts'  # The name of the app
