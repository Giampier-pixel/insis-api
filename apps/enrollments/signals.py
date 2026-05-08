from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.enrollments.models import Enrollment


@receiver(post_save, sender=Enrollment)
def send_enrollment_confirmation_signal(sender, instance, created, **kwargs):
    if created:
        try:
            from apps.notifications.tasks import send_enrollment_confirmation
            send_enrollment_confirmation.delay(instance.id)
        except Exception:
            pass
