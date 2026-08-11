import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings
from app.engine.models import LogEvent

def generate_magic_link(log: LogEvent) -> str:
    """Generate a signed JWT magic link for the RCA Chat UI."""
    now = datetime.now(timezone.utc)
    expiration = now + timedelta(hours=settings.MAGIC_LINK_EXPIRY_HOURS)
    
    # Ensure timestamp is string for serialization
    ts = log.timestamp.isoformat() if hasattr(log.timestamp, "isoformat") else str(log.timestamp)
    
    payload = {
        "sub": "triage-incident",
        "service_name": log.service_name,
        "trace_id": log.trace_id,
        "timestamp": ts,
        "exp": int(expiration.timestamp()),
        "iat": int(now.timestamp())
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    # Base URL for the Chat UI
    base_url = settings.CHAT_UI_BASE_URL
    return f"{base_url}?token={token}"
