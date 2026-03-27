from django.contrib import admin
from django.utils.html import format_html

from .models import Campaign, CampaignEmail, ABTest, CampaignSchedule


class CampaignScheduleInline(admin.StackedInline):
    model = CampaignSchedule
    extra = 0
    max_num = 1


class ABTestInline(admin.StackedInline):
    model = ABTest
    extra = 0
    max_num = 1


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = [
        "name", "organization", "status_badge", "campaign_type",
        "total_sent", "unique_opens", "unique_clicks",
        "open_rate_display", "click_rate_display",
        "sent_at", "created_at",
    ]
    list_filter = ["status", "campaign_type", "organization", "created_at"]
    search_fields = ["name", "subject"]
    readonly_fields = [
        "total_recipients", "total_sent", "total_delivered",
        "total_opens", "unique_opens", "total_clicks", "unique_clicks",
        "total_bounces", "total_unsubscribes", "total_complaints",
        "sent_at", "completed_at", "created_at", "updated_at",
    ]
    inlines = [CampaignScheduleInline, ABTestInline]
    filter_horizontal = ["contact_lists", "segments", "exclude_lists"]

    fieldsets = (
        ("Campaign Info", {
            "fields": ("name", "organization", "campaign_type", "status", "created_by"),
        }),
        ("Email Content", {
            "fields": ("subject", "preview_text", "from_name", "from_email",
                       "reply_to", "template", "html_content", "plain_text_content"),
        }),
        ("Recipients", {
            "fields": ("contact_lists", "segments", "exclude_lists"),
        }),
        ("Tracking", {
            "fields": ("track_opens", "track_clicks"),
        }),
        ("Statistics", {
            "classes": ("collapse",),
            "fields": (
                "total_recipients", "total_sent", "total_delivered",
                "total_opens", "unique_opens", "total_clicks", "unique_clicks",
                "total_bounces", "total_unsubscribes", "total_complaints",
            ),
        }),
        ("Timestamps", {
            "classes": ("collapse",),
            "fields": ("sent_at", "completed_at", "created_at", "updated_at"),
        }),
    )

    def status_badge(self, obj):
        colors = {
            "draft": "#6b7280",
            "scheduled": "#3b82f6",
            "sending": "#f59e0b",
            "sent": "#10b981",
            "paused": "#f59e0b",
            "cancelled": "#ef4444",
            "failed": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def open_rate_display(self, obj):
        return f"{obj.open_rate}%"
    open_rate_display.short_description = "Open Rate"

    def click_rate_display(self, obj):
        return f"{obj.click_rate}%"
    click_rate_display.short_description = "Click Rate"


@admin.register(CampaignEmail)
class CampaignEmailAdmin(admin.ModelAdmin):
    list_display = [
        "campaign", "contact", "status", "ab_variant",
        "sent_at", "opened_at", "clicked_at", "open_count", "click_count",
    ]
    list_filter = ["status", "ab_variant", "campaign"]
    search_fields = ["contact__email", "campaign__name"]
    readonly_fields = [
        "sent_at", "delivered_at", "opened_at", "clicked_at",
        "bounced_at", "open_count", "click_count", "created_at",
    ]
    raw_id_fields = ["campaign", "contact"]


@admin.register(ABTest)
class ABTestAdmin(admin.ModelAdmin):
    list_display = [
        "campaign", "test_variable", "winner_criteria",
        "variant_a_open_rate", "variant_b_open_rate",
        "winner_variant", "winner_selected_at",
    ]
    list_filter = ["test_variable", "winner_criteria"]
    readonly_fields = [
        "variant_a_sent", "variant_a_opens", "variant_a_clicks",
        "variant_b_sent", "variant_b_opens", "variant_b_clicks",
        "winner_variant", "winner_selected_at", "created_at",
    ]
