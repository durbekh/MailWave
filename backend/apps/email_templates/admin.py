from django.contrib import admin
from .models import EmailTemplate, TemplateCategory, TemplateBlock


@admin.register(TemplateCategory)
class TemplateCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "sort_order", "is_active", "created_at"]
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ["is_active"]
    search_fields = ["name"]
    ordering = ["sort_order"]


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = [
        "name", "organization", "template_type", "category",
        "is_active", "is_starred", "usage_count",
        "created_by", "created_at", "updated_at",
    ]
    list_filter = ["template_type", "category", "is_active", "is_starred", "organization"]
    search_fields = ["name", "description", "subject"]
    readonly_fields = ["usage_count", "created_at", "updated_at"]
    raw_id_fields = ["organization", "created_by"]

    fieldsets = (
        ("Template Info", {
            "fields": ("name", "description", "category", "template_type",
                       "organization", "created_by"),
        }),
        ("Content", {
            "fields": ("subject", "preview_text", "html_content", "json_content"),
        }),
        ("Display", {
            "fields": ("thumbnail", "is_active", "is_starred"),
        }),
        ("Usage", {
            "fields": ("usage_count", "created_at", "updated_at"),
        }),
    )


@admin.register(TemplateBlock)
class TemplateBlockAdmin(admin.ModelAdmin):
    list_display = ["name", "block_type", "organization", "is_global", "created_at"]
    list_filter = ["block_type", "is_global"]
    search_fields = ["name"]
