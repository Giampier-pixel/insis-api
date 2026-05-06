from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel


class EmailNotification(TimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SENT = "SENT", "Sent"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_notifications",
    )
    subject = models.CharField(max_length=255)
    body_template = models.CharField(max_length=100)
    context = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    task_id = models.CharField(max_length=255, blank=True)
    notification_type = models.CharField(max_length=100, db_index=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Email Notification"
        verbose_name_plural = "Email Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "notification_type"], name="notif_user_type_idx"
            ),
            models.Index(fields=["status"], name="notif_status_idx"),
        ]

    def __str__(self):
        return f"[{self.status}] {self.notification_type} → {self.user.email}"
