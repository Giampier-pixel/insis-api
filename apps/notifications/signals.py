from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.assignments.models import CompletionRecord


@receiver(post_save, sender=CompletionRecord)
def send_assignment_notification_signal(sender, instance, created, **kwargs):
    if not created:
        return

    try:
        from apps.notifications.tasks import send_assignment_notification

        send_assignment_notification.delay(instance.id)
    except Exception:
        pass
