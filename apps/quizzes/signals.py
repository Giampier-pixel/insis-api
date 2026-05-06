from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from apps.quizzes.models import Attempt


@receiver(post_save, sender=Attempt)
def on_attempt_finished(sender, instance, **kwargs):
    if not instance.finished_at:
        return
    # Atomic update: only one process wins, preventing duplicate notifications
    updated = Attempt.objects.filter(pk=instance.pk, notified_at__isnull=True).update(
        notified_at=timezone.now()
    )
    if updated:
        try:
            from apps.notifications.tasks import send_quiz_result

            send_quiz_result.delay(instance.id)
        except Exception:
            pass
