import uuid
from django.db import models


class DailyStats(models.Model):
    """Aggregated daily statistics per organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="daily_stats",
    )
    date = models.DateField()
    emails_sent = models.IntegerField(default=0)
    emails_delivered = models.IntegerField(default=0)
    emails_opened = models.IntegerField(default=0)
    unique_opens = models.IntegerField(default=0)
    emails_clicked = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    bounces = models.IntegerField(default=0)
    unsubscribes = models.IntegerField(default=0)
    complaints = models.IntegerField(default=0)
    new_contacts = models.IntegerField(default=0)
    contacts_unsubscribed = models.IntegerField(default=0)
    campaigns_sent = models.IntegerField(default=0)
    automation_emails_sent = models.IntegerField(default=0)

    class Meta:
        unique_together = ["organization", "date"]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["organization", "-date"]),
        ]

    def __str__(self):
        return f"{self.organization.name} - {self.date}"

    @property
    def open_rate(self):
        if self.emails_sent == 0:
            return 0
        return round((self.unique_opens / self.emails_sent) * 100, 2)

    @property
    def click_rate(self):
        if self.emails_sent == 0:
            return 0
        return round((self.unique_clicks / self.emails_sent) * 100, 2)

    @property
    def bounce_rate(self):
        if self.emails_sent == 0:
            return 0
        return round((self.bounces / self.emails_sent) * 100, 2)


class CampaignClickEvent(models.Model):
    """Tracks individual link click events for analytics."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign_email = models.ForeignKey(
        "campaigns.CampaignEmail", on_delete=models.CASCADE,
        related_name="click_events",
    )
    url = models.URLField(max_length=2048)
    link_id = models.CharField(max_length=32, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-clicked_at"]
        indexes = [
            models.Index(fields=["campaign_email", "-clicked_at"]),
            models.Index(fields=["link_id"]),
        ]

    def __str__(self):
        return f"Click on {self.url[:60]}"


class CampaignOpenEvent(models.Model):
    """Tracks individual email open events for analytics."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign_email = models.ForeignKey(
        "campaigns.CampaignEmail", on_delete=models.CASCADE,
        related_name="open_events",
    )
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["campaign_email", "-opened_at"]),
        ]

    def __str__(self):
        return f"Open by {self.campaign_email.contact.email}"


class LinkClickSummary(models.Model):
    """Aggregated click stats per link in a campaign."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        "campaigns.Campaign", on_delete=models.CASCADE,
        related_name="link_summaries",
    )
    url = models.URLField(max_length=2048)
    link_id = models.CharField(max_length=32, blank=True)
    total_clicks = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    last_clicked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["campaign", "url"]
        ordering = ["-total_clicks"]

    def __str__(self):
        return f"{self.url[:60]} ({self.total_clicks} clicks)"
