"""
Tests for the campaigns app: campaign CRUD, sending, A/B testing.
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.accounts.models import User, Organization, Plan
from apps.campaigns.models import Campaign, CampaignEmail, ABTest, CampaignSchedule
from apps.campaigns.services import CampaignService
from apps.contacts.models import Contact, ContactList
from utils.exceptions import CampaignNotReady


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class CampaignTestBase(TestCase):
    """Base test class for campaign tests."""

    def setUp(self):
        self.client = APIClient()
        self.plan = Plan.objects.create(
            name="Professional",
            tier=Plan.PlanTier.PROFESSIONAL,
            monthly_email_limit=50000,
            max_contacts=10000,
            ab_testing_enabled=True,
        )
        self.organization = Organization.objects.create(
            name="Campaign Test Org",
            slug="campaign-test-org",
            plan=self.plan,
            default_from_email="noreply@test.com",
            default_from_name="Test Sender",
        )
        self.user = User.objects.create_user(
            email="campaigner@test.com",
            password="CampaignP@ss123!",
            first_name="Campaign",
            last_name="Tester",
            organization=self.organization,
            role=User.Role.OWNER,
        )
        self.client.force_authenticate(user=self.user)

        self.contact_list = ContactList.objects.create(
            organization=self.organization,
            name="Main List",
            created_by=self.user,
        )
        # Create some contacts
        for i in range(5):
            contact = Contact.objects.create(
                organization=self.organization,
                email=f"contact{i}@example.com",
                first_name=f"Contact",
                last_name=f"{i}",
            )
            contact.lists.add(self.contact_list)


class CampaignCRUDTests(CampaignTestBase):
    """Test campaign CRUD operations."""

    def test_create_campaign(self):
        data = {
            "name": "Test Campaign",
            "subject": "Hello World",
            "html_content": "<h1>Hello {{first_name}}</h1><p>This is a test.</p>",
            "contact_list_ids": [str(self.contact_list.id)],
        }
        response = self.client.post("/api/campaigns/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Test Campaign")
        self.assertEqual(response.data["status"], "draft")

    def test_list_campaigns(self):
        Campaign.objects.create(
            organization=self.organization,
            name="Campaign 1",
            subject="Subject 1",
            created_by=self.user,
        )
        Campaign.objects.create(
            organization=self.organization,
            name="Campaign 2",
            subject="Subject 2",
            created_by=self.user,
        )
        response = self.client.get("/api/campaigns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_update_campaign_draft(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="Draft Campaign",
            subject="Old Subject",
            created_by=self.user,
        )
        data = {"subject": "Updated Subject"}
        response = self.client.patch(
            f"/api/campaigns/{campaign.id}/", data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign.refresh_from_db()
        self.assertEqual(campaign.subject, "Updated Subject")

    def test_duplicate_campaign(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="Original Campaign",
            subject="Test Subject",
            html_content="<p>Content</p>",
            created_by=self.user,
        )
        campaign.contact_lists.add(self.contact_list)

        response = self.client.post(f"/api/campaigns/{campaign.id}/duplicate/")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Original Campaign (Copy)")
        self.assertEqual(response.data["status"], "draft")

    def test_filter_campaigns_by_status(self):
        Campaign.objects.create(
            organization=self.organization, name="Draft",
            subject="S", status=Campaign.Status.DRAFT, created_by=self.user,
        )
        Campaign.objects.create(
            organization=self.organization, name="Sent",
            subject="S", status=Campaign.Status.SENT, created_by=self.user,
        )
        response = self.client.get("/api/campaigns/?status=draft")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["name"], "Draft")


class CampaignValidationTests(CampaignTestBase):
    """Test campaign validation logic."""

    def test_validate_campaign_missing_subject(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="No Subject",
            subject="",
            html_content="<p>Content</p>",
        )
        campaign.contact_lists.add(self.contact_list)

        with self.assertRaises(CampaignNotReady):
            CampaignService.validate_campaign_for_sending(campaign)

    def test_validate_campaign_missing_content(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="No Content",
            subject="Subject",
            html_content="",
        )
        campaign.contact_lists.add(self.contact_list)

        with self.assertRaises(CampaignNotReady):
            CampaignService.validate_campaign_for_sending(campaign)

    def test_validate_campaign_no_recipients(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="No Recipients",
            subject="Subject",
            html_content="<p>Content</p>",
        )
        with self.assertRaises(CampaignNotReady):
            CampaignService.validate_campaign_for_sending(campaign)

    def test_validate_campaign_email_limit_reached(self):
        self.organization.emails_sent_this_month = 50000
        self.organization.save()

        campaign = Campaign.objects.create(
            organization=self.organization,
            name="Over Limit",
            subject="Subject",
            html_content="<p>Content</p>",
        )
        campaign.contact_lists.add(self.contact_list)

        with self.assertRaises(CampaignNotReady) as ctx:
            CampaignService.validate_campaign_for_sending(campaign)
        self.assertIn("email limit", str(ctx.exception.message))

    def test_validate_ready_campaign_passes(self):
        campaign = Campaign.objects.create(
            organization=self.organization,
            name="Ready Campaign",
            subject="Subject",
            html_content="<p>Content</p>",
        )
        campaign.contact_lists.add(self.contact_list)

        result = CampaignService.validate_campaign_for_sending(campaign)
        self.assertTrue(result)


class CampaignModelTests(TestCase):
    """Test Campaign model methods and properties."""

    def test_open_rate_calculation(self):
        campaign = Campaign(total_sent=100, unique_opens=25)
        self.assertEqual(campaign.open_rate, 25.0)

    def test_click_rate_calculation(self):
        campaign = Campaign(total_sent=100, unique_clicks=10)
        self.assertEqual(campaign.click_rate, 10.0)

    def test_rates_with_zero_sent(self):
        campaign = Campaign(total_sent=0)
        self.assertEqual(campaign.open_rate, 0)
        self.assertEqual(campaign.click_rate, 0)
        self.assertEqual(campaign.bounce_rate, 0)
        self.assertEqual(campaign.unsubscribe_rate, 0)


class ABTestModelTests(TestCase):
    """Test A/B test model methods."""

    def setUp(self):
        org = Organization.objects.create(name="AB Test Org", slug="ab-test-org")
        self.campaign = Campaign.objects.create(
            organization=org,
            name="AB Campaign",
            subject="Subject",
            campaign_type=Campaign.CampaignType.AB_TEST,
        )
        self.ab_test = ABTest.objects.create(
            campaign=self.campaign,
            test_variable=ABTest.TestVariable.SUBJECT,
            variant_a_subject="Subject A",
            variant_b_subject="Subject B",
            variant_a_sent=100,
            variant_a_opens=30,
            variant_b_sent=100,
            variant_b_opens=25,
        )

    def test_variant_open_rates(self):
        self.assertEqual(self.ab_test.variant_a_open_rate, 30.0)
        self.assertEqual(self.ab_test.variant_b_open_rate, 25.0)

    def test_determine_winner_by_open_rate(self):
        self.ab_test.winner_criteria = ABTest.WinnerCriteria.OPEN_RATE
        winner = self.ab_test.determine_winner()
        self.assertEqual(winner, "A")

    def test_determine_winner_by_click_rate(self):
        self.ab_test.winner_criteria = ABTest.WinnerCriteria.CLICK_RATE
        self.ab_test.variant_a_clicks = 5
        self.ab_test.variant_b_clicks = 15
        self.ab_test.save()
        winner = self.ab_test.determine_winner()
        self.assertEqual(winner, "B")
