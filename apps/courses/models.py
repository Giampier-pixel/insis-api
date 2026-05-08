from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import SoftDeleteModel, TimestampedModel


class Course(TimestampedModel, SoftDeleteModel):
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="courses",
    )
    is_published = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Course"
        verbose_name_plural = "Courses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["instructor", "is_published"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
