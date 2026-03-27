"""
Celery configuration for MailWave project.
"""

import os

from celery import Celery
from celery.signals import task_failure
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("mailwave")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None,
                        args=None, kwargs=None, traceback=None, **kw):
    """Log task failures for monitoring."""
    logger.error(
        "Celery task failed: %s[%s] args=%s kwargs=%s exception=%s",
        sender.name if sender else "unknown",
        task_id,
        args,
        kwargs,
        exception,
    )


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
