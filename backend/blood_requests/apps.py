from django.apps import AppConfig


class BloodRequestsConfig(AppConfig):
    # Registration in backend/config/settings.py is a shared change coordinated by Arya
    # (STEP C). Never name this app "requests".
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blood_requests'
