from django.db.models.signals import post_save
from django.dispatch import receiver

# enrollments is loaded before assignments in INSTALLED_APPS, so this import is safe
from apps.enrollments.models import Enrollment


@receiver(post_save, sender=Enrollment)
def update_completion_record_on_enrollment_complete(sender, instance, **kwargs):
    """When a B2B enrollment is completed, mark the corresponding CompletionRecord."""
    if not instance.completed or not instance.course_assignment_id:
        return

    from apps.assignments.models import CompletionRecord

    CompletionRecord.objects.filter(
        assignment=instance.course_assignment,
        employee__user=instance.student,
        completed=False,
    ).update(
        completed=True,
        completed_at=instance.completed_at,
    )
