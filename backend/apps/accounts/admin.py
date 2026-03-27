from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Organization, Plan


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "email", "first_name", "last_name", "organization",
        "role", "is_active", "email_verified", "created_at",
    ]
    list_filter = ["role", "is_active", "email_verified", "organization"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal Info", {"fields": ("first_name", "last_name", "phone", "avatar", "timezone")}),
        ("Organization", {"fields": ("organization", "role")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active", "is_staff", "is_superuser",
                    "email_verified", "groups", "user_permissions",
                ),
            },
        ),
        ("Important Dates", {"fields": ("last_login", "created_at")}),
    )
    readonly_fields = ["created_at"]

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "first_name", "last_name",
                    "password1", "password2", "organization", "role",
                ),
            },
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "plan", "emails_sent_this_month",
        "is_active", "created_at",
    ]
    list_filter = ["is_active", "plan"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = [
        "name", "tier", "monthly_email_limit", "max_contacts",
        "price_monthly", "is_active",
    ]
    list_filter = ["is_active", "tier"]
