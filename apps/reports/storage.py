from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone


def _local_save(object_path, content):
    saved_path = default_storage.save(object_path, ContentFile(content))
    expires_at = timezone.now() + timedelta(minutes=30)
    return {
        "object_path": saved_path,
        "signed_url": default_storage.url(saved_path),
        "expires_at": expires_at,
    }


def _gcs_save(object_path, content, content_type):
    from google.cloud import storage  # type: ignore

    bucket = storage.Client().bucket(settings.GCS_BUCKET_NAME)
    blob = bucket.blob(object_path)
    blob.upload_from_string(content, content_type=content_type)
    expires_at = timezone.now() + timedelta(minutes=30)
    return {
        "object_path": object_path,
        "signed_url": blob.generate_signed_url(expiration=expires_at),
        "expires_at": expires_at,
    }


def save_report_export(job, content):
    extension = job.file_format
    object_path = str(
        Path("reports")
        / str(job.company_id)
        / f"{job.pk}-{job.report_type}.{extension}"
    )
    content_type = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if job.file_format == "xlsx"
        else "text/csv"
    )

    if getattr(settings, "USE_GCS", False) and getattr(settings, "GCS_BUCKET_NAME", ""):
        try:
            return _gcs_save(object_path, content, content_type)
        except ImportError:
            pass

    return _local_save(object_path, content)
