from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.enrollments.models import Enrollment, LessonProgress


@receiver(post_save, sender=Enrollment)
def send_enrollment_confirmation_signal(sender, instance, created, **kwargs):
    if created:
        try:
            from apps.notifications.tasks import send_enrollment_confirmation

            send_enrollment_confirmation.delay(instance.id)
        except Exception:
            pass


@receiver(post_save, sender=LessonProgress)
def check_course_completion_signal(sender, instance, **kwargs):
    if not instance.completed:
        return

    enrollment = instance.enrollment
    if enrollment.completed:
        return

    from apps.courses.models import Lesson

    total = Lesson.objects.filter(
        course=enrollment.course,
        is_published=True,
    ).count()

    if total == 0:
        return

    done = enrollment.lesson_progresses.filter(completed=True).count()

    if done >= total:
        enrollment.mark_completed()
        try:
            from apps.notifications.tasks import send_course_completion

            send_course_completion.delay(enrollment.id)
        except Exception:
            pass
