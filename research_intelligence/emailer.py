"""Email rendering and delivery for daily intelligence reports."""
from __future__ import annotations

import html
import smtplib
from email.message import EmailMessage
from typing import Any, Dict, Optional

import httpx
from loguru import logger

from config import get_settings


settings = get_settings()


class EmailDeliveryError(RuntimeError):
    """Raised when a configured provider cannot deliver mail."""


def build_daily_email_html(report: Dict[str, Any]) -> str:
    """Render a professional HTML email body."""
    top_updates = report.get("top_updates", [])
    worth = report.get("worth_exploring", [])
    emerging = report.get("emerging_signals", [])
    ignore = report.get("ignore_for_now", [])

    def update_item(item: Dict[str, Any]) -> str:
        tags = " ".join(f"<span class='tag'>{html.escape(str(tag))}</span>" for tag in item.get("category_tags", []))
        link = item.get("url") or "#"
        title = html.escape(item.get("title") or "Untitled update")
        brief = html.escape(item.get("brief") or "")
        why = html.escape(item.get("why_it_matters") or "")
        action = html.escape(item.get("recommended_action") or "Monitor")
        impact = html.escape(str(item.get("impact_score", "")))
        source_type = html.escape(item.get("source_type") or "source")
        thumbnail = item.get("thumbnail_url")
        image = (
            f"<img src='{html.escape(thumbnail)}' alt='' class='thumb'>"
            if isinstance(thumbnail, str) and thumbnail.startswith(("http://", "https://"))
            else ""
        )
        return f"""
        <tr>
            <td>
                {image}
                <a href="{html.escape(link)}" class="title">{title}</a>
                <div class="meta"><span>{source_type}</span> {tags}</div>
                <p>{brief}</p>
                <p>{why}</p>
                <p><strong>Action:</strong> {action}</p>
            </td>
            <td class="score">{impact}</td>
        </tr>
        """

    def compact_list(items: list[Dict[str, Any]]) -> str:
        if not items:
            return "<p class='muted'>No strong signals in this section.</p>"
        return "<ul>" + "".join(
            f"<li><a href='{html.escape(item.get('url') or '#')}'>{html.escape(item.get('title') or 'Untitled')}</a></li>"
            for item in items
        ) + "</ul>"

    rows = "".join(update_item(item) for item in top_updates)
    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ margin: 0; padding: 0; background: #f4f6f8; color: #111827; font-family: Arial, sans-serif; }}
    .wrap {{ max-width: 760px; margin: 0 auto; background: #ffffff; }}
    .header {{ padding: 28px 32px; background: #111827; color: #ffffff; }}
    .header h1 {{ margin: 0; font-size: 22px; }}
    .header p {{ margin: 8px 0 0; color: #cbd5e1; }}
    .section {{ padding: 24px 32px; border-bottom: 1px solid #e5e7eb; }}
    h2 {{ margin: 0 0 16px; font-size: 17px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ vertical-align: top; padding: 14px 0; border-top: 1px solid #edf2f7; }}
    .score {{ width: 80px; text-align: right; font-weight: 700; color: #0f766e; }}
    .title {{ color: #1d4ed8; font-weight: 700; text-decoration: none; }}
    .tag {{ display: inline-block; padding: 2px 7px; margin: 6px 4px 0 0; border-radius: 999px; background: #e0f2fe; color: #075985; font-size: 12px; }}
    .meta {{ margin-top: 4px; }}
    .thumb {{ width: 96px; height: 64px; object-fit: cover; float: right; margin: 0 0 8px 14px; border-radius: 6px; }}
    p {{ line-height: 1.5; }}
    .muted {{ color: #6b7280; }}
    ul {{ margin: 0; padding-left: 18px; }}
    li {{ margin: 8px 0; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>{html.escape(report.get("subject") or "Daily AI Intelligence Brief")}</h1>
      <p>{html.escape(report.get("summary") or "")}</p>
    </div>
    <div class="section">
      <h2>Top 20 Updates</h2>
      <table>{rows or "<tr><td>No high-confidence updates were found.</td><td></td></tr>"}</table>
    </div>
    <div class="section">
      <h2>Worth Exploring This Week</h2>
      {compact_list(worth)}
    </div>
    <div class="section">
      <h2>Emerging Signals</h2>
      {compact_list(emerging)}
    </div>
    <div class="section">
      <h2>Ignore For Now</h2>
      {compact_list(ignore)}
    </div>
  </div>
</body>
</html>
"""


def build_daily_email_markdown(report: Dict[str, Any]) -> str:
    """Render a Markdown version suitable for storage/export."""
    lines = [f"# {report.get('subject', 'Daily AI Intelligence Brief')}", "", report.get("summary", ""), ""]
    lines.append("## Top 20 Updates")
    for index, item in enumerate(report.get("top_updates", []), 1):
        lines.extend(
            [
                f"{index}. [{item.get('title', 'Untitled')}]({item.get('url', '#')})",
                f"   - Brief: {item.get('brief', '')}",
                f"   - Category: {item.get('category') or item.get('source_type', '')}",
                f"   - Why it matters: {item.get('why_it_matters', '')}",
                f"   - Impact: {item.get('impact_score', '')}",
                f"   - Action: {item.get('recommended_action', 'Monitor')}",
            ]
        )
    for title, key in [
        ("Worth Exploring This Week", "worth_exploring"),
        ("Emerging Signals", "emerging_signals"),
        ("Ignore For Now", "ignore_for_now"),
    ]:
        lines.extend(["", f"## {title}"])
        items = report.get(key, [])
        if not items:
            lines.append("No strong signals.")
        for item in items:
            lines.append(f"- [{item.get('title', 'Untitled')}]({item.get('url', '#')})")
    return "\n".join(lines)


class EmailSender:
    """Send email through SMTP, SendGrid, or Resend based on environment config."""

    def __init__(self, provider: Optional[str] = None) -> None:
        self.provider = provider or settings.email_provider

    async def send(self, to_email: str, subject: str, html_body: str, text_body: str = "") -> Dict[str, Any]:
        if not to_email:
            raise EmailDeliveryError("Team email is not configured")
        if self.provider == "disabled":
            raise EmailDeliveryError("Email provider is disabled")
        if self.provider == "smtp":
            return self._send_smtp(to_email, subject, html_body, text_body)
        if self.provider == "sendgrid":
            return await self._send_sendgrid(to_email, subject, html_body, text_body)
        if self.provider == "resend":
            return await self._send_resend(to_email, subject, html_body, text_body)
        raise EmailDeliveryError(f"Unsupported email provider: {self.provider}")

    def _send_smtp(self, to_email: str, subject: str, html_body: str, text_body: str) -> Dict[str, Any]:
        if not settings.smtp_host:
            raise EmailDeliveryError("SMTP_HOST is not configured")

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = settings.email_from
        message["To"] = to_email
        message.set_content(text_body or "Daily intelligence brief attached as HTML.")
        message.add_alternative(html_body, subtype="html")

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_username and settings.smtp_password:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return {"provider": "smtp", "status": "sent"}
        except Exception as exc:
            logger.error(f"SMTP delivery failed: {exc}")
            raise EmailDeliveryError(str(exc)) from exc

    async def _send_sendgrid(self, to_email: str, subject: str, html_body: str, text_body: str) -> Dict[str, Any]:
        if not settings.sendgrid_api_key:
            raise EmailDeliveryError("SENDGRID_API_KEY is not configured")
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.email_from},
            "subject": subject,
            "content": [
                {"type": "text/plain", "value": text_body or subject},
                {"type": "text/html", "value": html_body},
            ],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {settings.sendgrid_api_key}"},
                json=payload,
            )
        if response.status_code >= 300:
            raise EmailDeliveryError(f"SendGrid failed with {response.status_code}: {response.text[:200]}")
        return {"provider": "sendgrid", "status": "sent"}

    async def _send_resend(self, to_email: str, subject: str, html_body: str, text_body: str) -> Dict[str, Any]:
        if not settings.resend_api_key:
            raise EmailDeliveryError("RESEND_API_KEY is not configured")
        payload = {
            "from": settings.email_from,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body or subject,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
        if response.status_code >= 300:
            raise EmailDeliveryError(f"Resend failed with {response.status_code}: {response.text[:200]}")
        return {"provider": "resend", "status": "sent"}
