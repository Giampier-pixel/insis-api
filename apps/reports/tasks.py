from celery import shared_task

from django.utils import timezone


@shared_task
def generate_report_export(job_id):
    from apps.reports.exporters import export_report
    from apps.reports.models import ReportExportJob
    from apps.reports.storage import save_report_export

    try:
        job = ReportExportJob.objects.select_related("company").get(pk=job_id)
    except ReportExportJob.DoesNotExist:
        return {"status": "not_found"}

    job.status = ReportExportJob.Status.RUNNING
    job.started_at = timezone.now()
    job.error_message = ""
    job.save(update_fields=["status", "started_at", "error_message", "updated_at"])

    try:
        content = export_report(job.report_type, job.file_format, job.company)
        saved = save_report_export(job, content)
        job.status = ReportExportJob.Status.READY
        job.gcs_object_path = saved["object_path"]
        job.signed_url = saved["signed_url"]
        job.signed_url_expires_at = saved["expires_at"]
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "gcs_object_path",
                "signed_url",
                "signed_url_expires_at",
                "finished_at",
                "updated_at",
            ]
        )
        return {"status": "ready", "job_id": job.pk}
    except Exception as exc:
        job.status = ReportExportJob.Status.FAILED
        job.error_message = str(exc)[:1000]
        job.finished_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_message",
                "finished_at",
                "updated_at",
            ]
        )
        return {"status": "failed", "job_id": job.pk}
