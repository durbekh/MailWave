"""
Celery tasks for automation workflow processing.
"""

import logging
from celery import shared_task
from django.utils import timezone

from .models import AutomationWorkflow, AutomationEnrollment
from .services import AutomationEngine

logger = logging.getLogger(__name__)


@shared_task
def process_pending_steps():
    """
    Process all pending automation steps.
    Runs on a schedule (e.g., every 60 seconds) via Celery Beat.
    """
    now = timezone.now()

    pending_enrollments = AutomationEnrollment.objects.filter(
        status=AutomationEnrollment.Status.ACTIVE,
        next_action_at__lte=now,
        workflow__status=AutomationWorkflow.Status.ACTIVE,
    ).select_related(
        "workflow", "contact", "current_step",
    )[:500]  # Process in batches of 500

    processed = 0
    failed = 0

    for enrollment in pending_enrollments:
        try:
            AutomationEngine.process_enrollment(enrollment)
            processed += 1
        except Exception as e:
            failed += 1
            logger.error(
                "Failed to process enrollment %s: %s",
                enrollment.id, str(e), exc_info=True,
            )

    if processed > 0 or failed > 0:
        logger.info(
            "Automation step processing: processed=%d, failed=%d",
            processed, failed,
        )


@shared_task
def enroll_contacts_for_trigger(workflow_id, trigger_data):
    """
    Enroll contacts based on a trigger event.
    Called when a trigger condition is met (e.g., contact subscribes to a list).
    """
    try:
        workflow = AutomationWorkflow.objects.get(
            id=workflow_id,
            status=AutomationWorkflow.Status.ACTIVE,
        )
    except AutomationWorkflow.DoesNotExist:
        logger.warning("Workflow %s not found or not active", workflow_id)
        return

    contact_ids = trigger_data.get("contact_ids", [])

    enrolled = 0
    skipped = 0

    for contact_id in contact_ids:
        if AutomationEnrollment.objects.filter(
            workflow=workflow, contact_id=contact_id,
        ).exists():
            skipped += 1
            continue

        try:
            AutomationEngine.enroll_contact(workflow, contact_id)
            enrolled += 1
        except Exception as e:
            logger.error(
                "Failed to enroll contact %s in workflow %s: %s",
                contact_id, workflow_id, str(e),
            )

    logger.info(
        "Trigger enrollment for workflow %s: enrolled=%d, skipped=%d",
        workflow_id, enrolled, skipped,
    )


@shared_task
def cleanup_stale_enrollments():
    """
    Clean up enrollments that have been stuck in active status too long.
    Runs daily to catch any enrollments that may have gotten stuck.
    """
    from datetime import timedelta

    stale_threshold = timezone.now() - timedelta(days=90)

    stale = AutomationEnrollment.objects.filter(
        status=AutomationEnrollment.Status.ACTIVE,
        enrolled_at__lt=stale_threshold,
    )

    count = stale.count()
    if count > 0:
        stale.update(
            status=AutomationEnrollment.Status.EXITED,
            exited_at=timezone.now(),
            exit_reason="Exceeded maximum enrollment duration (90 days)",
        )
        logger.info("Cleaned up %d stale enrollments", count)


@shared_task
def update_automation_stats(workflow_id):
    """Recalculate automation stats from enrollment data."""
    try:
        workflow = AutomationWorkflow.objects.get(id=workflow_id)
    except AutomationWorkflow.DoesNotExist:
        return

    enrollments = workflow.enrollments.all()

    workflow.total_enrolled = enrollments.count()
    workflow.total_completed = enrollments.filter(
        status=AutomationEnrollment.Status.COMPLETED,
    ).count()
    workflow.total_exited = enrollments.filter(
        status=AutomationEnrollment.Status.EXITED,
    ).count()
    workflow.currently_active = enrollments.filter(
        status=AutomationEnrollment.Status.ACTIVE,
    ).count()

    workflow.save(update_fields=[
        "total_enrolled", "total_completed",
        "total_exited", "currently_active",
    ])
