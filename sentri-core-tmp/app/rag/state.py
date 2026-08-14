from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict, NotRequired
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class RCAResult(BaseModel):
    hypothesis: str = Field(description="The primary hypothesis for the root cause of the incident based on logs and code.")
    confidence_score: int = Field(description="Confidence score from 0 to 100")
    suggested_fix: str = Field(description="Actionable next step to verify or fix the issue.")
    github_permalink: Optional[str] = Field(None, description="The specific file or line in GitHub most likely responsible, if code was retrieved.")

class IncidentState(TypedDict):
    messages: NotRequired[List[BaseMessage]]
    service_name: NotRequired[str]
    trace_id: NotRequired[Optional[str]]
    timestamp: NotRequired[Optional[str]]
    retrieved_logs: NotRequired[Optional[List[Dict[str, Any]]]]
    retrieved_code: NotRequired[Optional[List[str]]]
    context_score: NotRequired[float]
    rca: NotRequired[Optional[RCAResult]]
