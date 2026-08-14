import httpx
import logging
from app.core.config import settings
from app.engine.models import LogEvent

logger = logging.getLogger(__name__)

async def dispatch_slack_alert(team: str, log: LogEvent, magic_link: str):
    """Send an asynchronous alert to a Slack Webhook."""
    if not settings.SLACK_WEBHOOK_URL:
        logger.info(f"[SLACK SIMULATION] Alert for {team}: {log.message}")
        logger.info(f"[SLACK SIMULATION] Magic Link: {magic_link}")
        return

    payload = {
        "text": f"New Incident in {log.service_name}",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {log.severity} Alert: {log.service_name}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Team:*\n{team}"},
                    {"type": "mrkdwn", "text": f"*Environment:*\n{log.environment or 'N/A'}"},
                    {"type": "mrkdwn", "text": f"*Trace ID:*\n`{log.trace_id or 'N/A'}`"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```\n{log.message}\n```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Start RCA Chat 🔍"
                        },
                        "style": "primary",
                        "url": magic_link,
                        "action_id": "start_rca"
                    }
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(settings.SLACK_WEBHOOK_URL, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully dispatched Slack alert to {team}")
    except httpx.HTTPError as e:
        logger.error(f"Failed to dispatch Slack alert: {e}")
