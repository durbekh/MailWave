import uuid
from django.db import models
from django.conf import settings


class Tag(models.Model):
    """Tags for categorizing contacts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="tags"
    )
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default="#6366f1")  # Hex color
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["organization", "name"]
        ordering = ["name"]

    def __str__(self):
        return self.name


class ContactList(models.Model):
    """List of contacts for organizing subscribers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="contact_lists"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    double_optin = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def contact_count(self):
        return self.contacts.filter(status=Contact.Status.SUBSCRIBED).count()

    @property
    def unsubscribed_count(self):
        return self.contacts.filter(status=Contact.Status.UNSUBSCRIBED).count()


class Contact(models.Model):
    """Individual contact / subscriber."""

    class Status(models.TextChoices):
        SUBSCRIBED = "subscribed", "Subscribed"
        UNSUBSCRIBED = "unsubscribed", "Unsubscribed"
        BOUNCED = "bounced", "Bounced"
        CLEANED = "cleaned", "Cleaned"
        PENDING = "pending", "Pending"

    class Source(models.TextChoices):
        IMPORT = "import", "Import"
        API = "api", "API"
        FORM = "form", "Signup Form"
        MANUAL = "manual", "Manual"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="contacts"
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    company = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    custom_fields = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUBSCRIBED
    )
    source = models.CharField(
        max_length=20, choices=Source.choices, default=Source.MANUAL
    )
    lists = models.ManyToManyField(ContactList, related_name="contacts", blank=True)
    tags = models.ManyToManyField(Tag, related_name="contacts", blank=True)
    lead_score = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    last_emailed_at = models.DateTimeField(null=True, blank=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)
    last_clicked_at = models.DateTimeField(null=True, blank=True)
    total_emails_received = models.IntegerField(default=0)
    total_opens = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["organization", "email"]
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "email"]),
            models.Index(fields=["unsubscribe_token"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.first_name} {self.last_name})".strip()

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def engagement_rate(self):
        if self.total_emails_received == 0:
            return 0
        return round(
            (self.total_opens / self.total_emails_received) * 100, 2
        )

    def to_merge_dict(self):
        """Return a dictionary for merge tag replacement."""
        return {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "company": self.company,
            "city": self.city,
            "state": self.state,
            "country": self.country,
            "custom_fields": self.custom_fields,
        }


class Segment(models.Model):
    """Dynamic contact segment based on rules."""

    class MatchType(models.TextChoices):
        ALL = "all", "Match All Rules"
        ANY = "any", "Match Any Rule"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "accounts.Organization", on_delete=models.CASCADE, related_name="segments"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    match_type = models.CharField(
        max_length=10, choices=MatchType.choices, default=MatchType.ALL
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def get_contacts(self):
        """Evaluate segment rules and return matching contacts."""
        from django.db.models import Q

        contacts = Contact.objects.filter(
            organization=self.organization,
            status=Contact.Status.SUBSCRIBED,
        )

        rules = self.rules.all()
        if not rules.exists():
            return contacts.none()

        filters = []
        for rule in rules:
            q = rule.to_q()
            if q is not None:
                filters.append(q)

        if not filters:
            return contacts.none()

        if self.match_type == self.MatchType.ALL:
            combined = filters[0]
            for f in filters[1:]:
                combined &= f
        else:
            combined = filters[0]
            for f in filters[1:]:
                combined |= f

        return contacts.filter(combined).distinct()

    @property
    def contact_count(self):
        return self.get_contacts().count()


class SegmentRule(models.Model):
    """Individual rule within a segment."""

    class Field(models.TextChoices):
        EMAIL = "email", "Email"
        FIRST_NAME = "first_name", "First Name"
        LAST_NAME = "last_name", "Last Name"
        COMPANY = "company", "Company"
        CITY = "city", "City"
        STATE = "state", "State"
        COUNTRY = "country", "Country"
        SOURCE = "source", "Source"
        LEAD_SCORE = "lead_score", "Lead Score"
        TOTAL_OPENS = "total_opens", "Total Opens"
        TOTAL_CLICKS = "total_clicks", "Total Clicks"
        SUBSCRIBED_AT = "subscribed_at", "Subscribed Date"
        LAST_OPENED_AT = "last_opened_at", "Last Opened"
        LAST_CLICKED_AT = "last_clicked_at", "Last Clicked"
        TAG = "tag", "Tag"
        LIST = "list", "List"

    class Operator(models.TextChoices):
        EQUALS = "equals", "Equals"
        NOT_EQUALS = "not_equals", "Not Equals"
        CONTAINS = "contains", "Contains"
        NOT_CONTAINS = "not_contains", "Not Contains"
        STARTS_WITH = "starts_with", "Starts With"
        ENDS_WITH = "ends_with", "Ends With"
        GREATER_THAN = "greater_than", "Greater Than"
        LESS_THAN = "less_than", "Less Than"
        IS_SET = "is_set", "Is Set"
        IS_NOT_SET = "is_not_set", "Is Not Set"
        BEFORE = "before", "Before"
        AFTER = "after", "After"
        IN_LIST = "in_list", "In List"
        NOT_IN_LIST = "not_in_list", "Not In List"
        HAS_TAG = "has_tag", "Has Tag"
        NOT_HAS_TAG = "not_has_tag", "Does Not Have Tag"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    segment = models.ForeignKey(
        Segment, on_delete=models.CASCADE, related_name="rules"
    )
    field = models.CharField(max_length=30, choices=Field.choices)
    operator = models.CharField(max_length=20, choices=Operator.choices)
    value = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.field} {self.operator} {self.value}"

    def to_q(self):
        """Convert rule to a Django Q object."""
        from django.db.models import Q
        from django.utils.dateparse import parse_datetime

        field = self.field
        op = self.operator
        val = self.value

        # Handle tag and list lookups
        if field == "tag":
            if op == self.Operator.HAS_TAG:
                return Q(tags__id=val)
            elif op == self.Operator.NOT_HAS_TAG:
                return ~Q(tags__id=val)
            return None

        if field == "list":
            if op == self.Operator.IN_LIST:
                return Q(lists__id=val)
            elif op == self.Operator.NOT_IN_LIST:
                return ~Q(lists__id=val)
            return None

        # Handle numeric fields
        numeric_fields = ["lead_score", "total_opens", "total_clicks"]
        if field in numeric_fields:
            try:
                val = int(val)
            except (ValueError, TypeError):
                return None

        # Build Q object based on operator
        if op == self.Operator.EQUALS:
            return Q(**{field: val})
        elif op == self.Operator.NOT_EQUALS:
            return ~Q(**{field: val})
        elif op == self.Operator.CONTAINS:
            return Q(**{f"{field}__icontains": val})
        elif op == self.Operator.NOT_CONTAINS:
            return ~Q(**{f"{field}__icontains": val})
        elif op == self.Operator.STARTS_WITH:
            return Q(**{f"{field}__istartswith": val})
        elif op == self.Operator.ENDS_WITH:
            return Q(**{f"{field}__iendswith": val})
        elif op == self.Operator.GREATER_THAN:
            return Q(**{f"{field}__gt": val})
        elif op == self.Operator.LESS_THAN:
            return Q(**{f"{field}__lt": val})
        elif op == self.Operator.IS_SET:
            return ~Q(**{field: ""}) & Q(**{f"{field}__isnull": False})
        elif op == self.Operator.IS_NOT_SET:
            return Q(**{field: ""}) | Q(**{f"{field}__isnull": True})
        elif op == self.Operator.BEFORE:
            dt = parse_datetime(val)
            if dt:
                return Q(**{f"{field}__lt": dt})
        elif op == self.Operator.AFTER:
            dt = parse_datetime(val)
            if dt:
                return Q(**{f"{field}__gt": dt})

        return None
