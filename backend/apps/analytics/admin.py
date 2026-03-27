from django.contrib import admin
from .models import DailyStats, CampaignClickEvent, CampaignOpenEvent, LinkClickSummary


@admin.register(DailyStats)
class DailyStatsAdmin(admin.ModelAdmin):
    list_display = [
        "organization", "date", "emails_sent", "emails_delivered",
        "unique_opens", "unique_clicks", "bounces", "unsubscribes",
        "new_contacts", "open_rate_display",
    ]
    list_filter = ["organization", "date"]
    date_hierarchy = "date"
    readonly_fields = [
        "emails_sent", "emails_delivered", "emails_opened",
        "unique_opens", "emails_clicked", "unique_clicks",
        "bounces", "unsubscribes", "complaints",
        "new_contacts", "contacts_unsubscribed",
        "campaigns_sent", "automation_emails_sent",
    ]

    def open_rate_display(self, obj):
        return f"{obj.open_rate}%"
    open_rate_display.short_description = "Open Rate"


@admin.register(CampaignClickEvent)
class CampaignClickEventAdmin(admin.ModelAdmin):
    list_display = [
        "campaign_email", "url_short", "device_type",
        "browser", "country", "clicked_at",
    ]
    list_filter = ["device_type", "browser", "country"]
    search_fields = ["url", "campaign_email__contact__email"]
    readonly_fields = ["clicked_at"]
    raw_id_fields = ["campaign_email"]

    def url_short(self, obj):
        return obj.url[:80] if len(obj.url) > 80 else obj.url
    url_short.short_description = "URL"


@admin.register(CampaignOpenEvent)
class CampaignOpenEventAdmin(admin.ModelAdmin):
    list_display = [
        "campaign_email", "device_type", "browser",
        "country", "opened_at",
    ]
    list_filter = ["device_type", "browser", "country"]
    readonly_fields = ["opened_at"]
    raw_id_fields = ["campaign_email"]


@admin.register(LinkClickSummary)
class LinkClickSummaryAdmin(admin.ModelAdmin):
    list_display = [
        "campaign", "url_short", "total_clicks",
        "unique_clicks", "last_clicked_at",
    ]
    list_filter = ["campaign"]
    readonly_fields = ["total_clicks", "unique_clicks", "last_clicked_at"]

    def url_short(self, obj):
        return obj.url[:80] if len(obj.url) > 80 else obj.url
    url_short.short_description = "URL"
