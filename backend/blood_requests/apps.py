from django.apps import AppConfig


class BloodRequestsConfig(AppConfig):
    # Registered in backend/config/settings.py (approved, BC-D017–BC-D022).
    # Never name this app "requests".
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'blood_requests'
