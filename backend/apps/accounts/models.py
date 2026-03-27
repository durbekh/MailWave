import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class Plan(models.Model):
    """Subscription plan for organizations."""

    class PlanTier(models.TextChoices):
        FREE = "free", "Free"
        STARTER = "starter", "Starter"
        PROFESSIONAL = "professional", "Professional"
        ENTERPRISE = "enterprise", "Enterprise"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, choices=PlanTier.choices, unique=True)
    monthly_email_limit = models.IntegerField(default=1000)
    max_contacts = models.IntegerField(default=500)
    max_campaigns_per_month = models.IntegerField(default=10)
    max_automation_sequences = models.IntegerField(default=3)
    ab_testing_enabled = models.BooleanField(default=False)
    advanced_analytics = models.BooleanField(default=False)
    custom_templates = models.BooleanField(default=False)
    priority_support = models.BooleanField(default=False)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["price_monthly"]

    def __str__(self):
        return f"{self.name} ({self.tier})"


class Organization(models.Model):
    """Organization / team account."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    plan = models.ForeignKey(
        Plan, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="organizations",
    )
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to="org_logos/", blank=True, null=True)
    default_from_email = models.EmailField(blank=True)
    default_from_name = models.CharField(max_length=255, blank=True)
    default_reply_to = models.EmailField(blank=True)
    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)
    emails_sent_this_month = models.IntegerField(default=0)
    billing_cycle_start = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def email_limit_reached(self):
        if self.plan:
            return self.emails_sent_this_month >= self.plan.monthly_email_limit
        return True

    @property
    def remaining_emails(self):
        if self.plan:
            return max(0, self.plan.monthly_email_limit - self.emails_sent_this_month)
        return 0


class User(AbstractUser):
    """Custom user model with email as the primary identifier."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        EDITOR = "editor", "Editor"
        VIEWER = "viewer", "Viewer"

    username = None
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, null=True, blank=True,
        related_name="members",
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EDITOR)
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    timezone = models.CharField(max_length=50, default="UTC")
    email_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def has_org_permission(self, permission_level):
        """Check if user has sufficient organization role."""
        role_hierarchy = {
            self.Role.VIEWER: 0,
            self.Role.EDITOR: 1,
            self.Role.ADMIN: 2,
            self.Role.OWNER: 3,
        }
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(permission_level, 0)
