import uuid
from django.db import models
from django.conf import settings


class TemplateCategory(models.Model):
    """Categories for organizing email templates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name (e.g., 'mail', 'star')")
    sort_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Template Categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class EmailTemplate(models.Model):
    """Reusable email template with drag-and-drop builder support."""

    class TemplateType(models.TextChoices):
        SYSTEM = "system", "System Template"
        CUSTOM = "custom", "Custom Template"
        SHARED = "shared", "Shared Template"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="email_templates", null=True, blank=True,
    )
    category = models.ForeignKey(
        TemplateCategory, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="templates",
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=500, blank=True)
    preview_text = models.CharField(max_length=255, blank=True)
    html_content = models.TextField(blank=True)
    json_content = models.JSONField(
        default=dict, blank=True,
        help_text="Structured content for the drag-and-drop editor",
    )
    thumbnail = models.ImageField(
        upload_to="template_thumbnails/", blank=True, null=True,
    )
    template_type = models.CharField(
        max_length=20, choices=TemplateType.choices, default=TemplateType.CUSTOM,
    )
    is_active = models.BooleanField(default=True)
    is_starred = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="created_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["organization", "template_type"]),
            models.Index(fields=["organization", "-updated_at"]),
        ]

    def __str__(self):
        return self.name

    def duplicate(self, user=None):
        """Create a copy of this template."""
        new_template = EmailTemplate.objects.create(
            organization=self.organization,
            category=self.category,
            name=f"{self.name} (Copy)",
            description=self.description,
            subject=self.subject,
            preview_text=self.preview_text,
            html_content=self.html_content,
            json_content=self.json_content,
            template_type=self.TemplateType.CUSTOM,
            created_by=user,
        )
        return new_template

    @property
    def merge_tags(self):
        """Extract merge tags used in the template."""
        import re
        tags = set()
        patterns = [
            r'\{\{(\w+)\}\}',
            r'\{\{custom_fields\.(\w+)\}\}',
        ]
        content = f"{self.html_content} {self.subject} {self.preview_text}"
        for pattern in patterns:
            matches = re.findall(pattern, content)
            tags.update(matches)
        return sorted(tags)


class TemplateBlock(models.Model):
    """Reusable content block for the template builder."""

    class BlockType(models.TextChoices):
        HEADER = "header", "Header"
        TEXT = "text", "Text Block"
        IMAGE = "image", "Image"
        BUTTON = "button", "Button"
        DIVIDER = "divider", "Divider"
        SPACER = "spacer", "Spacer"
        COLUMNS = "columns", "Columns"
        SOCIAL = "social", "Social Links"
        FOOTER = "footer", "Footer"
        HTML = "html", "Custom HTML"
        MENU = "menu", "Navigation Menu"
        VIDEO = "video", "Video"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE,
        related_name="template_blocks", null=True, blank=True,
    )
    name = models.CharField(max_length=255)
    block_type = models.CharField(max_length=20, choices=BlockType.choices)
    html_content = models.TextField(blank=True)
    json_config = models.JSONField(
        default=dict, blank=True,
        help_text="Block-specific configuration and styling",
    )
    is_global = models.BooleanField(
        default=False,
        help_text="Available to all organizations if True",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["block_type", "name"]

    def __str__(self):
        return f"{self.get_block_type_display()}: {self.name}"
