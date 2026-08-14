import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from app.engine.models import LogEvent

logger = logging.getLogger(__name__)

def _send_email_sync(recipient: str, subject: str, html_body: str):
    """Synchronous SMTP email sender."""
    if not settings.SMTP_SERVER or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD or not settings.SMTP_FROM_EMAIL:
        logger.warning("SMTP configuration is incomplete. Skipping email dispatch.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    
    # Handle multiple recipients separated by commas
    recipient_list = [r.strip() for r in recipient.split(",")]
    msg["To"] = ", ".join(recipient_list)

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, recipient_list, msg.as_string())
        logger.info(f"Successfully dispatched Email alert to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")

async def dispatch_email_alert(team: str, log: LogEvent, magic_link: str):
    """Asynchronously dispatches an incident email with a magic link."""
    # Determine recipient
    recipient = settings.ALERT_TO_EMAIL
    if not recipient:
        logger.warning(f"No ALERT_TO_EMAIL configured to receive alert for {team}")
        return

    subject = f"[Sentri Alert] {log.severity} in {log.service_name}"
    
    html_body = f"""
    <html>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f4f4f5; padding: 20px; color: #18181b;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #e4e4e7; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
          <div style="background-color: #ef4444; color: #ffffff; padding: 20px; text-align: center;">
            <h2 style="margin: 0;">New Incident Detected</h2>
          </div>
          <div style="padding: 24px;">
            <p style="margin-top: 0;"><strong>Service:</strong> {log.service_name}</p>
            <p><strong>Severity:</strong> {log.severity}</p>
            <p><strong>Team:</strong> {team}</p>
            <p><strong>Message:</strong></p>
            <pre style="background-color: #f4f4f5; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 14px;">{log.message}</pre>
            
            <div style="text-align: center; margin-top: 32px; margin-bottom: 16px;">
              <a href="{magic_link}" style="display: inline-block; background-color: #a855f7; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-size: 16px;">
                Analyze with Sentri
              </a>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    # Offload the blocking SMTP call to a thread pool
    await asyncio.to_thread(_send_email_sync, recipient, subject, html_body)
