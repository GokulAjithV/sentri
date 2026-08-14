from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LogEvent(BaseModel):
    timestamp: datetime
    service_name: str
    owner: Optional[str] = None
    severity: str
    trace_id: Optional[str] = None
    message: str
    stack_trace: Optional[str] = None
    environment: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
