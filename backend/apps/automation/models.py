import uuid
from django.db import models
from django.conf import settings


class AutomationWorkflow(models.Model):
    """Automation workflow / sequence definition."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    class TriggerType(models.TextChoices):
        SUBSCRIPTION = "subscription", "Subscriber Joins List"
        TAG_ADDED = "tag_added", "Tag Added"
        FORM_SUBMIT = "form_submit", "Form Submitted"
        DATE_FIELD = "date_field", "Date-Based"
        API_EVENT = "api_event", "API Event"
        MANUAL = "manual", "Manual Enrollment"
        CAMPAIGN_ACTIVITY = "campaign_activity", "Campaign Activity"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="automations",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT,
    )
    trigger_type = models.CharField(
        max_length=30, choices=TriggerType.choices, default=TriggerType.SUBSCRIPTION,
    )
    trigger_config = models.JSONField(
        default=dict, blank=True,
        help_text="Trigger-specific configuration (e.g., list_id, tag_id, event_name)",
    )
    # Stats
    total_enrolled = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    total_exited = models.IntegerField(default=0)
    currently_active = models.IntegerField(default=0)
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name="automations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return self.name

    @property
    def step_count(self):
        return self.steps.count()

    @property
    def conversion_rate(self):
        if self.total_enrolled == 0:
            return 0
        return round((self.total_completed / self.total_enrolled) * 100, 2)


class AutomationStep(models.Model):
    """Individual step in an automation workflow."""

    class StepType(models.TextChoices):
        SEND_EMAIL = "send_email", "Send Email"
        WAIT_DELAY = "wait_delay", "Wait / Delay"
        WAIT_UNTIL = "wait_until", "Wait Until Condition"
        CONDITION = "condition", "If/Else Condition"
        ADD_TAG = "add_tag", "Add Tag"
        REMOVE_TAG = "remove_tag", "Remove Tag"
        ADD_TO_LIST = "add_to_list", "Add to List"
        REMOVE_FROM_LIST = "remove_from_list", "Remove from List"
        UPDATE_FIELD = "update_field", "Update Contact Field"
        WEBHOOK = "webhook", "Send Webhook"
        NOTIFY_TEAM = "notify_team", "Notify Team"
        GOAL = "goal", "Goal / Conversion"
        EXIT = "exit", "Exit Automation"

    class DelayUnit(models.TextChoices):
        MINUTES = "minutes", "Minutes"
        HOURS = "hours", "Hours"
        DAYS = "days", "Days"
        WEEKS = "weeks", "Weeks"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        AutomationWorkflow, on_delete=models.CASCADE, related_name="steps",
    )
    step_type = models.CharField(max_length=30, choices=StepType.choices)
    name = models.CharField(max_length=255, blank=True)
    position = models.IntegerField(default=0, help_text="Order within the workflow")
    # Email step config
    email_template = models.ForeignKey(
        "email_templates.EmailTemplate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="automation_steps",
    )
    email_subject = models.CharField(max_length=500, blank=True)
    email_content = models.TextField(blank=True)
    # Delay step config
    delay_amount = models.IntegerField(default=0)
    delay_unit = models.CharField(
        max_length=10, choices=DelayUnit.choices,
        default=DelayUnit.DAYS, blank=True,
    )
    # Condition step config
    condition_config = models.JSONField(
        default=dict, blank=True,
        help_text="Condition rules: field, operator, value",
    )
    yes_next_step = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="condition_yes_from",
    )
    no_next_step = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="condition_no_from",
    )
    # Action config (tag_id, list_id, field_name/value, webhook_url)
    action_config = models.JSONField(
        default=dict, blank=True,
        help_text="Action-specific parameters",
    )
    # Stats for this step
    total_entered = models.IntegerField(default=0)
    total_completed = models.IntegerField(default=0)
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        indexes = [
            models.Index(fields=["workflow", "position"]),
        ]

    def __str__(self):
        return f"Step {self.position}: {self.name or self.get_step_type_display()}"

    def get_delay_seconds(self):
        """Convert delay amount and unit into seconds."""
        multipliers = {
            self.DelayUnit.MINUTES: 60,
            self.DelayUnit.HOURS: 3600,
            self.DelayUnit.DAYS: 86400,
            self.DelayUnit.WEEKS: 604800,
        }
        return self.delay_amount * multipliers.get(self.delay_unit, 86400)

    def get_next_step(self):
        """Get the next sequential step in the workflow."""
        return self.workflow.steps.filter(
            position__gt=self.position, is_active=True,
        ).first()


class AutomationEnrollment(models.Model):
    """Tracks a contact's progress through an automation workflow."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        EXITED = "exited", "Exited"
        PAUSED = "paused", "Paused"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(
        AutomationWorkflow, on_delete=models.CASCADE, related_name="enrollments",
    )
    contact = models.ForeignKey(
        "contacts.Contact", on_delete=models.CASCADE, related_name="automation_enrollments",
    )
    current_step = models.ForeignKey(
        AutomationStep, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="current_enrollments",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE,
    )
    next_action_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the next step should execute (after delay)",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    exited_at = models.DateTimeField(null=True, blank=True)
    exit_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-enrolled_at"]
        unique_together = ["workflow", "contact"]
        indexes = [
            models.Index(fields=["workflow", "status"]),
            models.Index(fields=["status", "next_action_at"]),
        ]

    def __str__(self):
        return f"{self.contact.email} in {self.workflow.name}"


class AutomationStepLog(models.Model):
    """Log of actions taken for each enrollment step."""

    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"
        WAITING = "waiting", "Waiting"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    enrollment = models.ForeignKey(
        AutomationEnrollment, on_delete=models.CASCADE, related_name="step_logs",
    )
    step = models.ForeignKey(
        AutomationStep, on_delete=models.CASCADE, related_name="logs",
    )
    result = models.CharField(
        max_length=20, choices=Result.choices, default=Result.SUCCESS,
    )
    details = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["executed_at"]

    def __str__(self):
        return f"{self.step} - {self.result}"
