"""
Email sending utility with tracking, rate limiting, and provider abstraction.
"""

import hashlib
import logging
import time
import uuid
from urllib.parse import urlencode, quote

from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.template import Template, Context
from premailer import transform

from utils.exceptions import EmailSendError, RateLimitExceeded

logger = logging.getLogger(__name__)

TRANSPARENT_PIXEL_GIF = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00"
    b"\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
)


class EmailSender:
    """Handles sending emails with tracking, personalization, and rate limiting."""

    def __init__(self):
        self.rate_limit_per_second = settings.EMAIL_RATE_LIMIT_PER_SECOND
        self.rate_limit_per_day = settings.EMAIL_RATE_LIMIT_PER_DAY
        self.tracking_pixel_url = settings.TRACKING_PIXEL_URL
        self.click_tracking_url = settings.CLICK_TRACKING_URL

    def _check_rate_limit(self, organization_id):
        """Check if the organization has exceeded its rate limit."""
        second_key = f"email_rate:{organization_id}:second:{int(time.time())}"
        day_key = f"email_rate:{organization_id}:day:{time.strftime('%Y-%m-%d')}"

        second_count = cache.get(second_key, 0)
        day_count = cache.get(day_key, 0)

        if second_count >= self.rate_limit_per_second:
            raise RateLimitExceeded(
                f"Rate limit exceeded: {self.rate_limit_per_second} emails per second"
            )

        if day_count >= self.rate_limit_per_day:
            raise RateLimitExceeded(
                f"Daily limit exceeded: {self.rate_limit_per_day} emails per day"
            )

        cache.set(second_key, second_count + 1, timeout=2)
        cache.set(day_key, day_count + 1, timeout=86400)

    def personalize_content(self, html_content, contact_data):
        """Replace merge tags with contact-specific data."""
        template = Template(html_content)
        context = Context({
            "first_name": contact_data.get("first_name", ""),
            "last_name": contact_data.get("last_name", ""),
            "email": contact_data.get("email", ""),
            "company": contact_data.get("company", ""),
            "custom_fields": contact_data.get("custom_fields", {}),
        })

        # Also handle {{merge_tag}} style replacements
        rendered = template.render(context)
        for key, value in contact_data.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value))

        return rendered

    def inject_tracking_pixel(self, html_content, campaign_email_id):
        """Inject a 1x1 tracking pixel into the email HTML."""
        tracking_url = (
            f"{self.tracking_pixel_url}?ceid={campaign_email_id}"
        )
        pixel_tag = f'<img src="{tracking_url}" width="1" height="1" alt="" style="display:none;" />'

        soup = BeautifulSoup(html_content, "html.parser")
        body = soup.find("body")
        if body:
            from bs4 import Tag
            pixel = BeautifulSoup(pixel_tag, "html.parser")
            body.append(pixel)
            return str(soup)

        return html_content + pixel_tag

    def rewrite_links_for_tracking(self, html_content, campaign_email_id):
        """Rewrite all links to go through the click tracking endpoint."""
        soup = BeautifulSoup(html_content, "html.parser")

        for link in soup.find_all("a", href=True):
            original_url = link["href"]

            # Skip mailto, tel, and unsubscribe links
            if original_url.startswith(("mailto:", "tel:", "#")):
                continue

            link_id = hashlib.md5(
                f"{campaign_email_id}:{original_url}".encode()
            ).hexdigest()[:12]

            params = urlencode({
                "ceid": campaign_email_id,
                "lid": link_id,
                "url": original_url,
            })
            link["href"] = f"{self.click_tracking_url}?{params}"

        return str(soup)

    def add_unsubscribe_link(self, html_content, unsubscribe_url):
        """Ensure unsubscribe link is present in the email."""
        if "unsubscribe" not in html_content.lower():
            unsubscribe_html = (
                f'<div style="text-align:center;padding:20px;font-size:12px;color:#999;">'
                f'<a href="{unsubscribe_url}" style="color:#999;">Unsubscribe</a> from these emails.'
                f'</div>'
            )
            soup = BeautifulSoup(html_content, "html.parser")
            body = soup.find("body")
            if body:
                unsub = BeautifulSoup(unsubscribe_html, "html.parser")
                body.append(unsub)
                return str(soup)
            return html_content + unsubscribe_html
        return html_content

    def prepare_email(self, campaign_email_id, html_content, contact_data,
                      unsubscribe_url):
        """Prepare an email with tracking and personalization."""
        # Personalize content
        html = self.personalize_content(html_content, contact_data)

        # Inline CSS for email client compatibility
        try:
            html = transform(html)
        except Exception:
            logger.warning("Failed to inline CSS for email %s", campaign_email_id)

        # Add unsubscribe link
        html = self.add_unsubscribe_link(html, unsubscribe_url)

        # Inject tracking pixel
        html = self.inject_tracking_pixel(html, campaign_email_id)

        # Rewrite links for click tracking
        html = self.rewrite_links_for_tracking(html, campaign_email_id)

        return html

    def send_email(self, to_email, subject, html_content, from_email=None,
                   from_name=None, reply_to=None, headers=None,
                   campaign_email_id=None, organization_id=None):
        """Send a single email."""

        if organization_id:
            self._check_rate_limit(organization_id)

        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        from_name = from_name or settings.DEFAULT_FROM_NAME
        from_address = f"{from_name} <{from_email}>"

        email_headers = headers or {}
        if campaign_email_id:
            email_headers["X-Mailwave-Campaign-Email-ID"] = str(campaign_email_id)
            email_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Create plain text version
        from html2text import html2text
        plain_text = html2text(html_content)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_text,
            from_email=from_address,
            to=[to_email],
            reply_to=[reply_to] if reply_to else None,
            headers=email_headers,
        )
        msg.attach_alternative(html_content, "text/html")

        try:
            msg.send(fail_silently=False)
            logger.info("Email sent to %s (campaign_email_id=%s)", to_email, campaign_email_id)
            return True
        except Exception as e:
            logger.error(
                "Failed to send email to %s: %s", to_email, str(e),
                exc_info=True,
            )
            raise EmailSendError(f"Failed to send email to {to_email}: {str(e)}")

    def send_batch(self, emails, organization_id=None):
        """
        Send a batch of emails.
        emails: list of dicts with keys: to_email, subject, html_content,
                campaign_email_id, contact_data, unsubscribe_url
        """
        results = {"sent": 0, "failed": 0, "errors": []}

        for email_data in emails:
            try:
                html = self.prepare_email(
                    campaign_email_id=email_data["campaign_email_id"],
                    html_content=email_data["html_content"],
                    contact_data=email_data["contact_data"],
                    unsubscribe_url=email_data["unsubscribe_url"],
                )

                self.send_email(
                    to_email=email_data["to_email"],
                    subject=email_data["subject"],
                    html_content=html,
                    campaign_email_id=email_data["campaign_email_id"],
                    organization_id=organization_id,
                )
                results["sent"] += 1

            except RateLimitExceeded:
                logger.warning("Rate limit hit during batch send")
                results["errors"].append({
                    "email": email_data["to_email"],
                    "error": "Rate limit exceeded",
                })
                break

            except EmailSendError as e:
                results["failed"] += 1
                results["errors"].append({
                    "email": email_data["to_email"],
                    "error": str(e),
                })

        return results


email_sender = EmailSender()
