from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.forms.models import model_to_dict

from .models import (
    ChangeLog, School, User, ClassSection, Subject, GradingScale,
    GradingPeriod, StudentEnrollment, Grade, Attendance, UserApplication
)

# List of models to track
TRACKED_MODELS = [
    School, User, ClassSection, Subject, GradingScale,
    GradingPeriod, StudentEnrollment, Grade, Attendance, UserApplication
]


def _create_changelog_entry(instance, action):
    try:
        data = model_to_dict(instance)
    except Exception:
        data = {}

    kwargs = {
        'model': instance.__class__.__name__,
        'object_id': str(getattr(instance, 'id', '')),
        'action': action,
        'data': data,
        'school': getattr(instance, 'school', None)
    }

    try:
        ChangeLog.objects.create(**kwargs)
    except Exception:
        # Avoid throwing errors from signal handlers
        pass


@receiver(post_save)
def handle_post_save(sender, instance, created, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    _create_changelog_entry(instance, 'create' if created else 'update')


@receiver(post_delete)
def handle_post_delete(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return
    _create_changelog_entry(instance, 'delete')
