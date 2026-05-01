"""
Celery configuration for INSIS API project.

Configures the Celery app, autodiscovery, and Beat schedule.
"""

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("insis")

# Load task modules from all registered Django apps.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps.
app.autodiscover_tasks()

# ============================================================
# Beat schedule — tareas periódicas
# ============================================================
app.conf.beat_schedule = {
    "inactivity-reminder": {
        "task": "apps.notifications.tasks.send_inactivity_reminder",
        "schedule": crontab(hour=9, minute=0),
    },
    "due-date-reminder": {
        "task": "apps.notifications.tasks.send_due_date_reminder",
        "schedule": crontab(hour=9, minute=30),
    },
    "weekly-progress-report": {
        "task": "apps.notifications.tasks.send_weekly_progress_report",
        "schedule": crontab(day_of_week=1, hour=8, minute=0),
    },
    "monthly-company-report": {
        "task": "apps.notifications.tasks.generate_monthly_company_report",
        "schedule": crontab(day_of_month=1, hour=7, minute=0),
    },
}
