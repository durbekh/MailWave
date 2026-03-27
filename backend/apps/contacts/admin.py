from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Contact, ContactList, Tag, Segment, SegmentRule


class ContactResource(resources.ModelResource):
    class Meta:
        model = Contact
        fields = (
            "id", "email", "first_name", "last_name", "company",
            "phone", "city", "state", "country", "status", "source",
            "lead_score", "subscribed_at",
        )
        import_id_fields = ["email"]


@admin.register(Contact)
class ContactAdmin(ImportExportModelAdmin):
    resource_class = ContactResource
    list_display = [
        "email", "first_name", "last_name", "organization",
        "status", "source", "lead_score", "total_opens",
        "total_clicks", "created_at",
    ]
    list_filter = ["status", "source", "organization"]
    search_fields = ["email", "first_name", "last_name", "company"]
    readonly_fields = [
        "unsubscribe_token", "total_emails_received", "total_opens",
        "total_clicks", "created_at", "updated_at",
    ]
    filter_horizontal = ["tags", "lists"]


@admin.register(ContactList)
class ContactListAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "is_default", "double_optin", "created_at"]
    list_filter = ["organization", "is_default"]
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "color", "created_at"]
    list_filter = ["organization"]
    search_fields = ["name"]


class SegmentRuleInline(admin.TabularInline):
    model = SegmentRule
    extra = 1


@admin.register(Segment)
class SegmentAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "match_type", "is_active", "created_at"]
    list_filter = ["organization", "is_active", "match_type"]
    search_fields = ["name"]
    inlines = [SegmentRuleInline]
