# -*- coding: utf-8 -*-
"""
Stage 4 – Brevo Transactional Email Dispatch
=============================================

Composes personalised, professionally-styled HTML outreach emails and
dispatches them via the Brevo (SendinBlue) transactional email API.

Created by Vaibhav Sonava
"""
from __future__ import annotations

from typing import List

from loguru import logger

from pipeline.models import DecisionMaker, EmailDraft

# ---------------------------------------------------------------------------
# HTML email template (inline CSS for maximum client compatibility)
# ---------------------------------------------------------------------------
_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:32px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.07);">
        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:28px 36px;">
            <h1 style="margin:0;color:#e2e8f0;font-size:20px;font-weight:600;letter-spacing:0.5px;">
              Partnership Opportunity
            </h1>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:32px 36px;color:#334155;font-size:15px;line-height:1.7;">
            <p style="margin:0 0 16px;">Hi <strong>{to_name}</strong>,</p>

            <p style="margin:0 0 16px;">
              I came across <strong>{company_name}</strong> and was genuinely impressed
              by the impact your team is making in the <strong>{industry}</strong> space.
              As {title_article} <strong>{title}</strong>, you're clearly driving
              meaningful innovation.
            </p>

            <p style="margin:0 0 16px;">
              At <strong>{sender_company}</strong>, we help forward-thinking companies
              like yours accelerate growth through AI-powered outreach automation and
              intelligent lead engagement. Our clients typically see a
              <strong>3–5× improvement</strong> in qualified pipeline within 90&nbsp;days.
            </p>

            <p style="margin:0 0 16px;">
              I'd love to share a brief case study relevant to {company_name} and
              explore whether there's a fit. Would you be open to a 15-minute call
              this week or next?
            </p>

            <p style="margin:0 0 24px;">Looking forward to connecting.</p>

            <!-- CTA Button -->
            <table role="presentation" cellpadding="0" cellspacing="0">
              <tr>
                <td style="border-radius:6px;background:#2563eb;">
                  <a href="mailto:{sender_email}?subject=Re:%20Partnership%20Opportunity"
                     style="display:inline-block;padding:12px 28px;color:#ffffff;font-size:14px;
                            font-weight:600;text-decoration:none;letter-spacing:0.3px;">
                    Let's Connect &rarr;
                  </a>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 36px;background:#f8fafc;border-top:1px solid #e2e8f0;
                      font-size:12px;color:#94a3b8;line-height:1.6;">
            Best regards,<br>
            <strong>{sender_name}</strong><br>
            {sender_email}
            <br><br>
            <em style="font-size:11px;">
              This email was sent by an automated outreach system.
              If you'd prefer not to hear from us, simply reply with "unsubscribe".
            </em>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


class BrevoStage:
    """Stage 4: Compose & send personalised outreach emails via Brevo."""

    def __init__(self, api_key: str, sender_email: str, sender_name: str) -> None:
        self.api_key = (api_key or "").strip()
        self.sender_email = (sender_email or "outreach@example.com").strip()
        self.sender_name = (sender_name or "Vaibhav Sonava").strip()

    # ------------------------------------------------------------------
    # Email composition
    # ------------------------------------------------------------------
    def _compose_email(self, dm: DecisionMaker) -> EmailDraft:
        """Build a personalised EmailDraft for a single DecisionMaker."""
        company_name = dm.company_domain.split(".")[0].capitalize()
        title_article = "an" if dm.title[0:1].upper() in ("A", "E", "I", "O", "U") else "a"

        subject = f"Quick question for {dm.name} at {company_name}"
        body = _EMAIL_TEMPLATE.format(
            to_name=dm.name.split()[0],  # first name only
            company_name=company_name,
            industry="technology",
            title=dm.title,
            title_article=title_article,
            sender_company="Subspace AI",
            sender_email=self.sender_email,
            sender_name=self.sender_name,
        )

        return EmailDraft(
            to_email=dm.email,
            to_name=dm.name,
            subject=subject,
            body_html=body,
            company_domain=dm.company_domain,
            decision_maker_title=dm.title,
        )

    # ------------------------------------------------------------------
    # Brevo dispatch via official SDK
    # ------------------------------------------------------------------
    def _send_via_brevo(self, draft: EmailDraft) -> bool:
        """Send a single email through the Brevo transactional API."""
        try:
            import sib_api_v3_sdk  # type: ignore[import-untyped]
        except ImportError:
            logger.error(
                "sib_api_v3_sdk is not installed. Run: pip install sib-api-v3-sdk"
            )
            return False

        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key["api-key"] = self.api_key

        api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            sender={"name": self.sender_name, "email": self.sender_email},
            to=[{"email": draft.to_email, "name": draft.to_name}],
            subject=draft.subject,
            html_content=draft.body_html,
        )

        try:
            api_response = api_instance.send_transac_email(send_smtp_email)
            logger.info(
                "Brevo email sent to {} – messageId: {}",
                draft.to_email,
                getattr(api_response, "message_id", "N/A"),
            )
            return True
        except Exception as exc:
            logger.error("Brevo send failed for {}: {}", draft.to_email, exc)
            return False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def run(
        self,
        decision_makers: List[DecisionMaker],
        input_domain: str,
        dry_run: bool = False,
    ) -> List[EmailDraft]:
        """
        Compose and (optionally) send outreach emails for all enriched
        decision-makers.

        Parameters
        ----------
        decision_makers:
            DecisionMakers enriched with email addresses.
        input_domain:
            The original target domain (used for logging context).
        dry_run:
            When ``True``, emails are composed and logged but **not** sent.

        Returns
        -------
        list[EmailDraft]
            All composed email drafts (sent or unsent).
        """
        logger.info(
            "✉️   Brevo stage – composing emails for {} decision-makers (dry_run={})",
            len(decision_makers),
            dry_run,
        )

        drafts: list[EmailDraft] = []
        eligible = [dm for dm in decision_makers if dm.email]

        if not eligible:
            logger.warning("No decision-makers with emails – nothing to send.")
            return drafts

        for dm in eligible:
            draft = self._compose_email(dm)
            drafts.append(draft)

            if dry_run:
                logger.info(
                    "[DRY-RUN] Would send to {} <{}> – subject: '{}'",
                    dm.name,
                    dm.email,
                    draft.subject,
                )
                continue

            if not self.api_key:
                logger.warning(
                    "Brevo API key is empty; draft created but NOT sent for {}.", dm.email
                )
                continue

            self._send_via_brevo(draft)

        logger.success(
            "Brevo stage complete – {} email drafts composed for domain '{}'.",
            len(drafts),
            input_domain,
        )
        return drafts
