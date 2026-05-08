from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import CustomUser


@receiver(post_save, sender=CustomUser)
def send_welcome_email_signal(sender, instance, created, **kwargs):
    if created:
        try:
            from apps.notifications.tasks import send_welcome_email

            send_welcome_email.delay(instance.id)
        except Exception:
            pass
