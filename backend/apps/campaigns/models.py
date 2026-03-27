import uuid
from django.db import models
from django.conf import settings


class Campaign(models.Model):
    """Email marketing campaign."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        PAUSED = "paused", "Paused"
        CANCELLED = "cancelled", "Cancelled"
        FAILED = "failed", "Failed"

    class CampaignType(models.TextChoices):
        REGULAR = "regular", "Regular"
        AB_TEST = "ab_test", "A/B Test"
        AUTOMATED = "automated", "Automated"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="campaigns"
    )
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=500)
    preview_text = models.CharField(max_length=255, blank=True)
    from_name = models.CharField(max_length=255, blank=True)
    from_email = models.EmailField(blank=True)
    reply_to = models.EmailField(blank=True)
    html_content = models.TextField(blank=True)
    plain_text_content = models.TextField(blank=True)
    template = models.ForeignKey(
        "email_templates.EmailTemplate", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="campaigns",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    campaign_type = models.CharField(
        max_length=20, choices=CampaignType.choices, default=CampaignType.REGULAR
    )
    # Recipients
    contact_lists = models.ManyToManyField(
        "contacts.ContactList", related_name="campaigns", blank=True
    )
    segments = models.ManyToManyField(
        "contacts.Segment", related_name="campaigns", blank=True
    )
    exclude_lists = models.ManyToManyField(
        "contacts.ContactList", related_name="excluded_campaigns", blank=True
    )
    # Tracking
    track_opens = models.BooleanField(default=True)
    track_clicks = models.BooleanField(default=True)
    # Stats (denormalized for quick access)
    total_recipients = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    total_delivered = models.IntegerField(default=0)
    total_opens = models.IntegerField(default=0)
    unique_opens = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    total_bounces = models.IntegerField(default=0)
    total_unsubscribes = models.IntegerField(default=0)
    total_complaints = models.IntegerField(default=0)
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="campaigns",
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "-created_at"]),
        ]

    def __str__(self):
        return self.name

    @property
    def open_rate(self):
        if self.total_sent == 0:
            return 0
        return round((self.unique_opens / self.total_sent) * 100, 2)

    @property
    def click_rate(self):
        if self.total_sent == 0:
            return 0
        return round((self.unique_clicks / self.total_sent) * 100, 2)

    @property
    def bounce_rate(self):
        if self.total_sent == 0:
            return 0
        return round((self.total_bounces / self.total_sent) * 100, 2)

    @property
    def unsubscribe_rate(self):
        if self.total_sent == 0:
            return 0
        return round((self.total_unsubscribes / self.total_sent) * 100, 2)

    def get_recipients(self):
        """Get all unique contacts for this campaign."""
        from apps.contacts.models import Contact

        contacts = Contact.objects.none()

        # Add contacts from lists
        for contact_list in self.contact_lists.all():
            contacts = contacts | contact_list.contacts.filter(
                status=Contact.Status.SUBSCRIBED
            )

        # Add contacts from segments
        for segment in self.segments.all():
            contacts = contacts | segment.get_contacts()

        # Exclude contacts from excluded lists
        for exclude_list in self.exclude_lists.all():
            contacts = contacts.exclude(
                id__in=exclude_list.contacts.values_list("id", flat=True)
            )

        return contacts.filter(status=Contact.Status.SUBSCRIBED).distinct()


class CampaignEmail(models.Model):
    """Individual email sent as part of a campaign."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        OPENED = "opened", "Opened"
        CLICKED = "clicked", "Clicked"
        BOUNCED = "bounced", "Bounced"
        FAILED = "failed", "Failed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="emails"
    )
    contact = models.ForeignKey(
        "contacts.Contact", on_delete=models.CASCADE, related_name="campaign_emails"
    )
    ab_variant = models.CharField(max_length=1, blank=True)  # 'A' or 'B'
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.QUEUED
    )
    subject_used = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    bounced_at = models.DateTimeField(null=True, blank=True)
    bounce_reason = models.TextField(blank=True)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ["campaign", "contact"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["contact", "status"]),
        ]

    def __str__(self):
        return f"{self.campaign.name} -> {self.contact.email}"


class ABTest(models.Model):
    """A/B test configuration for a campaign."""

    class TestVariable(models.TextChoices):
        SUBJECT = "subject", "Subject Line"
        CONTENT = "content", "Email Content"
        FROM_NAME = "from_name", "From Name"
        SEND_TIME = "send_time", "Send Time"

    class WinnerCriteria(models.TextChoices):
        OPEN_RATE = "open_rate", "Open Rate"
        CLICK_RATE = "click_rate", "Click Rate"
        MANUAL = "manual", "Manual Selection"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name="ab_test"
    )
    test_variable = models.CharField(
        max_length=20, choices=TestVariable.choices, default=TestVariable.SUBJECT
    )
    variant_a_subject = models.CharField(max_length=500, blank=True)
    variant_b_subject = models.CharField(max_length=500, blank=True)
    variant_a_content = models.TextField(blank=True)
    variant_b_content = models.TextField(blank=True)
    variant_a_from_name = models.CharField(max_length=255, blank=True)
    variant_b_from_name = models.CharField(max_length=255, blank=True)
    test_percentage = models.IntegerField(
        default=20,
        help_text="Percentage of recipients to use for the test (split evenly between variants)"
    )
    winner_criteria = models.CharField(
        max_length=20, choices=WinnerCriteria.choices, default=WinnerCriteria.OPEN_RATE
    )
    test_duration_hours = models.IntegerField(
        default=4,
        help_text="Hours to wait before selecting winner and sending to rest"
    )
    winner_variant = models.CharField(max_length=1, blank=True)  # 'A' or 'B'
    winner_selected_at = models.DateTimeField(null=True, blank=True)
    # Stats per variant
    variant_a_sent = models.IntegerField(default=0)
    variant_a_opens = models.IntegerField(default=0)
    variant_a_clicks = models.IntegerField(default=0)
    variant_b_sent = models.IntegerField(default=0)
    variant_b_opens = models.IntegerField(default=0)
    variant_b_clicks = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"A/B Test for {self.campaign.name}"

    @property
    def variant_a_open_rate(self):
        if self.variant_a_sent == 0:
            return 0
        return round((self.variant_a_opens / self.variant_a_sent) * 100, 2)

    @property
    def variant_b_open_rate(self):
        if self.variant_b_sent == 0:
            return 0
        return round((self.variant_b_opens / self.variant_b_sent) * 100, 2)

    @property
    def variant_a_click_rate(self):
        if self.variant_a_sent == 0:
            return 0
        return round((self.variant_a_clicks / self.variant_a_sent) * 100, 2)

    @property
    def variant_b_click_rate(self):
        if self.variant_b_sent == 0:
            return 0
        return round((self.variant_b_clicks / self.variant_b_sent) * 100, 2)

    def determine_winner(self):
        """Determine the winning variant based on criteria."""
        if self.winner_criteria == self.WinnerCriteria.OPEN_RATE:
            if self.variant_a_open_rate >= self.variant_b_open_rate:
                return "A"
            return "B"
        elif self.winner_criteria == self.WinnerCriteria.CLICK_RATE:
            if self.variant_a_click_rate >= self.variant_b_click_rate:
                return "A"
            return "B"
        return ""


class CampaignSchedule(models.Model):
    """Schedule configuration for a campaign."""

    class ScheduleType(models.TextChoices):
        IMMEDIATE = "immediate", "Send Immediately"
        SCHEDULED = "scheduled", "Schedule for Later"
        OPTIMAL = "optimal", "Send at Optimal Time"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.OneToOneField(
        Campaign, on_delete=models.CASCADE, related_name="schedule"
    )
    schedule_type = models.CharField(
        max_length=20, choices=ScheduleType.choices, default=ScheduleType.IMMEDIATE
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default="UTC")
    send_in_recipient_timezone = models.BooleanField(default=False)
    batch_size = models.IntegerField(
        default=500,
        help_text="Number of emails to send per batch"
    )
    batch_delay_seconds = models.IntegerField(
        default=10,
        help_text="Delay between batches in seconds"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Schedule for {self.campaign.name}"
