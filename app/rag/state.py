from typing import TypedDict, List, Dict, Any, Optional, NotRequired
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class RCAResult(BaseModel):
    hypothesis: str = Field(description="The primary hypothesis for the root cause of the incident.")
    confidence_score: int = Field(description="Confidence score from 0 to 100 based on the available logs.")
    suggested_fix: str = Field(description="Actionable next step or suggested fix.")

class IncidentState(TypedDict):
    messages: NotRequired[List[BaseMessage]]
    service_name: NotRequired[str]
    trace_id: NotRequired[Optional[str]]
    timestamp: NotRequired[Optional[str]]
    retrieved_logs: NotRequired[Optional[List[Dict[str, Any]]]]
    rca: NotRequired[Optional[RCAResult]]
