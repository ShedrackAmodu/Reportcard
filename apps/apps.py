from django.apps import AppConfig


class SchoolsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps"
    
    def ready(self):
        # Import signals to ensure change tracking is enabled
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
