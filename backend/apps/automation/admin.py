from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AutomationWorkflow, AutomationStep,
    AutomationEnrollment, AutomationStepLog,
)


class AutomationStepInline(admin.TabularInline):
    model = AutomationStep
    extra = 0
    ordering = ["position"]
    fields = [
        "position", "step_type", "name", "delay_amount", "delay_unit",
        "is_active", "total_entered", "total_completed",
    ]
    readonly_fields = ["total_entered", "total_completed"]


@admin.register(AutomationWorkflow)
class AutomationWorkflowAdmin(admin.ModelAdmin):
    list_display = [
        "name", "organization", "status_badge", "trigger_type",
        "step_count", "total_enrolled", "currently_active",
        "conversion_rate_display", "created_at",
    ]
    list_filter = ["status", "trigger_type", "organization"]
    search_fields = ["name", "description"]
    readonly_fields = [
        "total_enrolled", "total_completed", "total_exited",
        "currently_active", "created_at", "updated_at",
    ]
    inlines = [AutomationStepInline]

    def status_badge(self, obj):
        colors = {
            "draft": "#6b7280",
            "active": "#10b981",
            "paused": "#f59e0b",
            "archived": "#9ca3af",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{}; color:white; padding:3px 10px; '
            'border-radius:12px; font-size:11px;">{}</span>',
            color, obj.get_status_display(),
        )
    status_badge.short_description = "Status"

    def step_count(self, obj):
        return obj.steps.count()
    step_count.short_description = "Steps"

    def conversion_rate_display(self, obj):
        return f"{obj.conversion_rate}%"
    conversion_rate_display.short_description = "Conversion"


@admin.register(AutomationStep)
class AutomationStepAdmin(admin.ModelAdmin):
    list_display = [
        "workflow", "position", "step_type", "name",
        "is_active", "total_entered", "total_completed",
    ]
    list_filter = ["step_type", "is_active", "workflow"]
    readonly_fields = ["total_entered", "total_completed", "created_at", "updated_at"]


@admin.register(AutomationEnrollment)
class AutomationEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "contact", "workflow", "status", "current_step",
        "next_action_at", "enrolled_at", "completed_at",
    ]
    list_filter = ["status", "workflow"]
    search_fields = ["contact__email"]
    raw_id_fields = ["contact", "workflow", "current_step"]
    readonly_fields = ["enrolled_at"]


@admin.register(AutomationStepLog)
class AutomationStepLogAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "step", "result", "executed_at"]
    list_filter = ["result"]
    readonly_fields = ["executed_at"]
    raw_id_fields = ["enrollment", "step"]
