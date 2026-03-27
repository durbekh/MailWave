"""
Automation engine for processing workflow steps.
"""

import logging
from datetime import timedelta

import requests
from django.db import transaction
from django.utils import timezone

from apps.contacts.models import Contact, ContactList, Tag
from utils.email_sender import email_sender

from .models import (
    AutomationWorkflow,
    AutomationStep,
    AutomationEnrollment,
    AutomationStepLog,
)

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Core engine that processes automation workflow steps."""

    @staticmethod
    def enroll_contact(workflow, contact_id):
        """Enroll a contact in an automation workflow."""
        first_step = workflow.steps.filter(is_active=True).first()

        enrollment = AutomationEnrollment.objects.create(
            workflow=workflow,
            contact_id=contact_id,
            current_step=first_step,
            status=AutomationEnrollment.Status.ACTIVE,
            next_action_at=timezone.now(),
        )

        workflow.total_enrolled += 1
        workflow.currently_active += 1
        workflow.save(update_fields=["total_enrolled", "currently_active"])

        logger.info(
            "Contact %s enrolled in automation %s",
            contact_id, workflow.id,
        )

        return enrollment

    @staticmethod
    def process_enrollment(enrollment):
        """Process the current step for an enrollment."""
        if enrollment.status != AutomationEnrollment.Status.ACTIVE:
            return

        step = enrollment.current_step
        if not step:
            AutomationEngine._complete_enrollment(enrollment)
            return

        # Check if it's time to execute
        if enrollment.next_action_at and enrollment.next_action_at > timezone.now():
            return

        try:
            result = AutomationEngine._execute_step(enrollment, step)

            AutomationStepLog.objects.create(
                enrollment=enrollment,
                step=step,
                result=AutomationStepLog.Result.SUCCESS if result else AutomationStepLog.Result.FAILED,
                details={"step_type": step.step_type},
            )

            step.total_entered += 1
            if result:
                step.total_completed += 1
            step.save(update_fields=["total_entered", "total_completed"])

            # Move to next step
            if result:
                AutomationEngine._advance_to_next_step(enrollment, step)

        except Exception as e:
            logger.error(
                "Error processing step %s for enrollment %s: %s",
                step.id, enrollment.id, str(e), exc_info=True,
            )

            AutomationStepLog.objects.create(
                enrollment=enrollment,
                step=step,
                result=AutomationStepLog.Result.FAILED,
                error_message=str(e),
            )

            enrollment.status = AutomationEnrollment.Status.FAILED
            enrollment.save(update_fields=["status"])

    @staticmethod
    def _execute_step(enrollment, step):
        """Execute a specific automation step."""
        handlers = {
            AutomationStep.StepType.SEND_EMAIL: AutomationEngine._handle_send_email,
            AutomationStep.StepType.WAIT_DELAY: AutomationEngine._handle_wait_delay,
            AutomationStep.StepType.CONDITION: AutomationEngine._handle_condition,
            AutomationStep.StepType.ADD_TAG: AutomationEngine._handle_add_tag,
            AutomationStep.StepType.REMOVE_TAG: AutomationEngine._handle_remove_tag,
            AutomationStep.StepType.ADD_TO_LIST: AutomationEngine._handle_add_to_list,
            AutomationStep.StepType.REMOVE_FROM_LIST: AutomationEngine._handle_remove_from_list,
            AutomationStep.StepType.UPDATE_FIELD: AutomationEngine._handle_update_field,
            AutomationStep.StepType.WEBHOOK: AutomationEngine._handle_webhook,
            AutomationStep.StepType.NOTIFY_TEAM: AutomationEngine._handle_notify_team,
            AutomationStep.StepType.GOAL: AutomationEngine._handle_goal,
            AutomationStep.StepType.EXIT: AutomationEngine._handle_exit,
        }

        handler = handlers.get(step.step_type)
        if handler:
            return handler(enrollment, step)

        logger.warning("Unknown step type: %s", step.step_type)
        return False

    @staticmethod
    def _handle_send_email(enrollment, step):
        """Send an email to the enrolled contact."""
        contact = enrollment.contact

        html_content = step.email_content
        subject = step.email_subject

        if step.email_template:
            html_content = html_content or step.email_template.html_content
            subject = subject or step.email_template.subject

            step.email_template.usage_count += 1
            step.email_template.save(update_fields=["usage_count"])

        if not html_content or not subject:
            logger.error("Email step %s missing content or subject", step.id)
            return False

        org = enrollment.workflow.organization
        unsubscribe_url = f"https://{org.slug}.mailwave.io/unsubscribe/{contact.unsubscribe_token}/"

        prepared_html = email_sender.prepare_email(
            campaign_email_id=f"auto-{enrollment.id}-{step.id}",
            html_content=html_content,
            contact_data=contact.to_merge_dict(),
            unsubscribe_url=unsubscribe_url,
        )

        email_sender.send_email(
            to_email=contact.email,
            subject=subject,
            html_content=prepared_html,
            from_email=org.default_from_email,
            from_name=org.default_from_name,
            organization_id=str(org.id),
        )

        contact.total_emails_received += 1
        contact.last_emailed_at = timezone.now()
        contact.save(update_fields=["total_emails_received", "last_emailed_at"])

        return True

    @staticmethod
    def _handle_wait_delay(enrollment, step):
        """Set a delay before the next step."""
        delay_seconds = step.get_delay_seconds()
        enrollment.next_action_at = timezone.now() + timedelta(seconds=delay_seconds)
        enrollment.save(update_fields=["next_action_at"])
        return True

    @staticmethod
    def _handle_condition(enrollment, step):
        """Evaluate a condition and branch accordingly."""
        contact = enrollment.contact
        config = step.condition_config

        field = config.get("field", "")
        operator = config.get("operator", "equals")
        value = config.get("value", "")

        contact_value = getattr(contact, field, None)
        if contact_value is None:
            contact_value = contact.custom_fields.get(field, "")

        condition_met = False
        contact_str = str(contact_value).lower()
        value_str = str(value).lower()

        if operator == "equals":
            condition_met = contact_str == value_str
        elif operator == "not_equals":
            condition_met = contact_str != value_str
        elif operator == "contains":
            condition_met = value_str in contact_str
        elif operator == "greater_than":
            try:
                condition_met = float(contact_value) > float(value)
            except (ValueError, TypeError):
                condition_met = False
        elif operator == "less_than":
            try:
                condition_met = float(contact_value) < float(value)
            except (ValueError, TypeError):
                condition_met = False
        elif operator == "is_set":
            condition_met = bool(contact_value)
        elif operator == "is_not_set":
            condition_met = not bool(contact_value)

        if condition_met and step.yes_next_step:
            enrollment.current_step = step.yes_next_step
            enrollment.save(update_fields=["current_step"])
        elif not condition_met and step.no_next_step:
            enrollment.current_step = step.no_next_step
            enrollment.save(update_fields=["current_step"])

        return True

    @staticmethod
    def _handle_add_tag(enrollment, step):
        """Add a tag to the contact."""
        tag_id = step.action_config.get("tag_id")
        if tag_id:
            try:
                tag = Tag.objects.get(
                    id=tag_id,
                    organization=enrollment.workflow.organization,
                )
                enrollment.contact.tags.add(tag)
            except Tag.DoesNotExist:
                logger.warning("Tag %s not found for automation step %s", tag_id, step.id)
                return False
        return True

    @staticmethod
    def _handle_remove_tag(enrollment, step):
        """Remove a tag from the contact."""
        tag_id = step.action_config.get("tag_id")
        if tag_id:
            enrollment.contact.tags.remove(tag_id)
        return True

    @staticmethod
    def _handle_add_to_list(enrollment, step):
        """Add the contact to a list."""
        list_id = step.action_config.get("list_id")
        if list_id:
            try:
                contact_list = ContactList.objects.get(
                    id=list_id,
                    organization=enrollment.workflow.organization,
                )
                enrollment.contact.lists.add(contact_list)
            except ContactList.DoesNotExist:
                logger.warning("List %s not found for automation step %s", list_id, step.id)
                return False
        return True

    @staticmethod
    def _handle_remove_from_list(enrollment, step):
        """Remove the contact from a list."""
        list_id = step.action_config.get("list_id")
        if list_id:
            enrollment.contact.lists.remove(list_id)
        return True

    @staticmethod
    def _handle_update_field(enrollment, step):
        """Update a contact field."""
        field_name = step.action_config.get("field_name")
        field_value = step.action_config.get("field_value")

        if not field_name:
            return False

        contact = enrollment.contact

        if hasattr(contact, field_name):
            setattr(contact, field_name, field_value)
            contact.save(update_fields=[field_name])
        else:
            contact.custom_fields[field_name] = field_value
            contact.save(update_fields=["custom_fields"])

        return True

    @staticmethod
    def _handle_webhook(enrollment, step):
        """Send a webhook request."""
        url = step.action_config.get("webhook_url")
        method = step.action_config.get("method", "POST").upper()

        if not url:
            return False

        contact = enrollment.contact
        payload = {
            "event": "automation_step",
            "workflow_id": str(enrollment.workflow_id),
            "step_id": str(step.id),
            "contact": {
                "id": str(contact.id),
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "custom_fields": contact.custom_fields,
            },
        }

        try:
            if method == "POST":
                response = requests.post(url, json=payload, timeout=30)
            else:
                response = requests.get(url, params={"data": str(payload)}, timeout=30)

            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.error("Webhook failed for step %s: %s", step.id, str(e))
            return False

    @staticmethod
    def _handle_notify_team(enrollment, step):
        """Send a notification to team members."""
        notify_emails = step.action_config.get("notify_emails", [])
        message = step.action_config.get("message", "")

        contact = enrollment.contact
        notification_body = (
            f"Automation: {enrollment.workflow.name}\n"
            f"Contact: {contact.full_name} ({contact.email})\n"
            f"Step: {step}\n\n"
            f"{message}"
        )

        for notify_email in notify_emails:
            email_sender.send_email(
                to_email=notify_email,
                subject=f"[MailWave] Automation notification: {enrollment.workflow.name}",
                html_content=f"<pre>{notification_body}</pre>",
            )

        return True

    @staticmethod
    def _handle_goal(enrollment, step):
        """Mark a goal as reached -- completes the enrollment."""
        AutomationEngine._complete_enrollment(enrollment)
        return True

    @staticmethod
    def _handle_exit(enrollment, step):
        """Exit the automation early."""
        enrollment.status = AutomationEnrollment.Status.EXITED
        enrollment.exited_at = timezone.now()
        enrollment.exit_reason = step.action_config.get("reason", "Exit step reached")
        enrollment.save(update_fields=["status", "exited_at", "exit_reason"])

        workflow = enrollment.workflow
        workflow.total_exited += 1
        workflow.currently_active = max(0, workflow.currently_active - 1)
        workflow.save(update_fields=["total_exited", "currently_active"])

        return True

    @staticmethod
    def _advance_to_next_step(enrollment, current_step):
        """Move the enrollment to the next step in the workflow."""
        if current_step.step_type == AutomationStep.StepType.CONDITION:
            return  # Condition handler already sets next step

        next_step = current_step.get_next_step()

        if next_step:
            enrollment.current_step = next_step
            enrollment.next_action_at = timezone.now()
            enrollment.save(update_fields=["current_step", "next_action_at"])
        else:
            AutomationEngine._complete_enrollment(enrollment)

    @staticmethod
    def _complete_enrollment(enrollment):
        """Mark an enrollment as completed."""
        enrollment.status = AutomationEnrollment.Status.COMPLETED
        enrollment.completed_at = timezone.now()
        enrollment.current_step = None
        enrollment.save(update_fields=["status", "completed_at", "current_step"])

        workflow = enrollment.workflow
        workflow.total_completed += 1
        workflow.currently_active = max(0, workflow.currently_active - 1)
        workflow.save(update_fields=["total_completed", "currently_active"])

        logger.info(
            "Enrollment %s completed in automation %s",
            enrollment.id, workflow.id,
        )
