"""
Tests for the accounts app: user registration, login, organization management.
"""

import uuid
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Organization, Plan


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class AccountsTestBase(TestCase):
    """Base test class with common setup for account tests."""

    def setUp(self):
        self.client = APIClient()
        self.plan = Plan.objects.create(
            name="Free",
            tier=Plan.PlanTier.FREE,
            monthly_email_limit=1000,
            max_contacts=500,
            max_campaigns_per_month=10,
            max_automation_sequences=3,
        )
        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            plan=self.plan,
        )
        self.user = User.objects.create_user(
            email="owner@test.com",
            password="SecureP@ss123!",
            first_name="Test",
            last_name="Owner",
            organization=self.organization,
            role=User.Role.OWNER,
        )


class RegistrationTests(AccountsTestBase):
    """Test user registration flow."""

    def test_register_creates_user_and_organization(self):
        data = {
            "email": "newuser@example.com",
            "password": "StrongP@ssw0rd!",
            "password_confirm": "StrongP@ssw0rd!",
            "first_name": "New",
            "last_name": "User",
            "organization_name": "New Org",
        }
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("tokens", response.data)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], "newuser@example.com")

        # Verify organization was created
        user = User.objects.get(email="newuser@example.com")
        self.assertIsNotNone(user.organization)
        self.assertEqual(user.organization.name, "New Org")
        self.assertEqual(user.role, User.Role.OWNER)

    def test_register_with_duplicate_email_fails(self):
        data = {
            "email": "owner@test.com",
            "password": "StrongP@ssw0rd!",
            "password_confirm": "StrongP@ssw0rd!",
            "first_name": "Dup",
            "last_name": "User",
            "organization_name": "Dup Org",
        }
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_with_mismatched_passwords_fails(self):
        data = {
            "email": "newuser2@example.com",
            "password": "StrongP@ssw0rd!",
            "password_confirm": "DifferentP@ss!",
            "first_name": "New",
            "last_name": "User",
            "organization_name": "New Org 2",
        }
        response = self.client.post(reverse("register"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(AccountsTestBase):
    """Test user login flow."""

    def test_login_with_valid_credentials(self):
        data = {"email": "owner@test.com", "password": "SecureP@ss123!"}
        response = self.client.post(reverse("login"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("tokens", response.data)
        self.assertIn("access", response.data["tokens"])
        self.assertIn("refresh", response.data["tokens"])

    def test_login_with_wrong_password_fails(self):
        data = {"email": "owner@test.com", "password": "wrongpassword"}
        response = self.client.post(reverse("login"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_with_nonexistent_email_fails(self):
        data = {"email": "nobody@test.com", "password": "anypassword"}
        response = self.client.post(reverse("login"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProfileTests(AccountsTestBase):
    """Test user profile management."""

    def test_get_current_user_profile(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("me"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "owner@test.com")
        self.assertEqual(response.data["first_name"], "Test")

    def test_update_profile(self):
        self.client.force_authenticate(user=self.user)
        data = {"first_name": "Updated", "timezone": "US/Eastern"}
        response = self.client.patch(reverse("me"), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.timezone, "US/Eastern")


class OrganizationTests(AccountsTestBase):
    """Test organization management."""

    def test_get_current_organization(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse("organization-current"),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Test Org")

    def test_organization_email_limit_tracking(self):
        self.organization.emails_sent_this_month = 999
        self.organization.save()
        self.assertFalse(self.organization.email_limit_reached)
        self.assertEqual(self.organization.remaining_emails, 1)

        self.organization.emails_sent_this_month = 1000
        self.organization.save()
        self.assertTrue(self.organization.email_limit_reached)
        self.assertEqual(self.organization.remaining_emails, 0)

    def test_invite_member_requires_admin(self):
        viewer = User.objects.create_user(
            email="viewer@test.com",
            password="ViewerP@ss123!",
            organization=self.organization,
            role=User.Role.VIEWER,
        )
        self.client.force_authenticate(user=viewer)
        data = {"email": "new@test.com", "role": "editor"}
        response = self.client.post(
            reverse("organization-invite"), data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_invite_member(self):
        self.client.force_authenticate(user=self.user)
        data = {"email": "newmember@test.com", "role": "editor"}
        response = self.client.post(
            reverse("organization-invite"), data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            User.objects.filter(
                email="newmember@test.com", organization=self.organization,
            ).exists()
        )


class UserModelTests(TestCase):
    """Test User model methods."""

    def test_full_name_property(self):
        user = User(first_name="John", last_name="Doe")
        self.assertEqual(user.full_name, "John Doe")

    def test_full_name_with_empty_last_name(self):
        user = User(first_name="John", last_name="")
        self.assertEqual(user.full_name, "John")

    def test_has_org_permission_hierarchy(self):
        user = User(role=User.Role.ADMIN)
        self.assertTrue(user.has_org_permission(User.Role.EDITOR))
        self.assertTrue(user.has_org_permission(User.Role.VIEWER))
        self.assertFalse(user.has_org_permission(User.Role.OWNER))
