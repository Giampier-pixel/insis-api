from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import CustomUser, UserProfile


@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=CustomUser)
def send_welcome_email_signal(sender, instance, created, **kwargs):
    if created:
        try:
            from apps.notifications.tasks import send_welcome_email

            send_welcome_email.delay(instance.id)
        except Exception:
            pass
