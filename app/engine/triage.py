import logging
from datetime import datetime, timedelta, timezone
from app.engine.models import LogEvent
from app.core.config import settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for deduplication
# Key: (service_name, message_hash) -> Value: timestamp of last alert
_dedup_cache = {}

def is_severity_actionable(severity: str) -> bool:
    """Filter to act only on ERROR or WARN."""
    return severity.upper() in ["ERROR", "WARN"]

def is_duplicate(log: LogEvent) -> bool:
    """Check if this is a duplicate event within the dedup window."""
    now = datetime.now(timezone.utc)
    # Create a simple signature for the error
    signature = hash(f"{log.service_name}:{log.message}")
    
    if signature in _dedup_cache:
        last_seen = _dedup_cache[signature]
        if now - last_seen < timedelta(minutes=settings.DEDUP_WINDOW_MINUTES):
            return True
            
    # Update cache
    _dedup_cache[signature] = now
    
    # Cleanup old entries to prevent memory leak
    # In a real system, use Redis with TTL
    cutoff = now - timedelta(minutes=settings.DEDUP_WINDOW_MINUTES)
    keys_to_delete = [k for k, v in _dedup_cache.items() if v < cutoff]
    for k in keys_to_delete:
        del _dedup_cache[k]
        
    return False

def route_incident(log: LogEvent) -> str:
    """Determine the team/channel to notify."""
    # Dummy routing logic for now
    if log.owner:
        return log.owner
    # Fallback mappings
    mappings = {
        "crease-scoring-service": "team-crease-backend",
        "crease-lens": "team-crease-frontend"
    }
    return mappings.get(log.service_name, "team-general")

def process_log_event(log_data: dict):
    """Process a single log event through the triage pipeline."""
    try:
        payload = log_data.get("_source", log_data)
        log = LogEvent(**payload)
    except Exception as e:
        logger.error(f"Failed to parse log event: {e}")
        return

    if not is_severity_actionable(log.severity):
        logger.info(f"Discarding non-actionable log ({log.severity}): {log.message}")
        return

    if is_duplicate(log):
        logger.info(f"Suppressing duplicate log: {log.message}")
        return

    team = route_incident(log)
    logger.info(f"New actionable incident detected! Routing to {team}: {log.message}")
    
    # TODO: Generate magic link and trigger Notify Service
