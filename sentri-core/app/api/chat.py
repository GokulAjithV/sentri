import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.api.auth import verify_jwt_token
from app.rag.graph import build_graph
from app.rag.state import IncidentState
from langchain_core.messages import HumanMessage, BaseMessage

logger = logging.getLogger(__name__)
router = APIRouter()
graph = build_graph()

class ChatRequest(BaseModel):
    message: str
    # Pass history from client for simplicity instead of server-side checkpointer
    history: Optional[List[Dict[str, str]]] = [] 
    
@router.post("/chat")
async def chat_endpoint(request: ChatRequest, payload: dict = Depends(verify_jwt_token)):
    service_name = payload.get("service_name")
    trace_id = payload.get("trace_id")
    timestamp = payload.get("timestamp")
    
    if not service_name:
        raise HTTPException(status_code=400, detail="Invalid token payload")
        
    from langchain_core.messages import AIMessage
    # Convert dict history to LangChain messages
    messages = []
    for msg in (request.history or []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] in ["assistant", "ai", "system"]:
            messages.append(AIMessage(content=msg["content"]))
    
    # Add current message if it's not the INIT signal
    if request.message != "INIT":
        messages.append(HumanMessage(content=request.message))
        
    # We pass empty retrieved_logs for follow-ups, because in a real implementation
    # we would use a StateSaver checkpointer in LangGraph to persist the retrieved logs.
    # For this simplified endpoint without a database, we'll let LangGraph just 
    # reason without the logs for follow-ups, OR we can fetch them again.
    # To keep context, let's just always leave retrieved_logs as None so it fetches them.
    
    state: IncidentState = {
        "service_name": service_name,
        "trace_id": trace_id,
        "timestamp": timestamp,
        "messages": messages,
        "retrieved_logs": None,
        "rca": None
    }
    
    async def event_generator():
        try:
            async for event in graph.astream_events(state, version="v1"):
                kind = event["event"]
                
                # Stream LLM tokens for standard chat
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                        
                # Stream the RCA structured output when reasoning finishes
                elif kind == "on_chain_end":
                    name = event["name"]
                    if name == "reason_rca_node":
                        rca_output = event["data"]["output"].get("rca")
                        if rca_output:
                            # Send the structured RCA back
                            yield f"data: {json.dumps({'type': 'rca', 'rca': rca_output.dict()})}\n\n"
                            
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error in graph streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

class ExploreRequest(BaseModel):
    message: str
    service_name: str
    history: Optional[List[Dict[str, str]]] = []

@router.post("/chat/explore")
async def explore_endpoint(request: ExploreRequest):
    if not request.service_name:
        raise HTTPException(status_code=400, detail="service_name is required")
        
    from langchain_core.messages import AIMessage, HumanMessage
    messages = []
    for msg in (request.history or []):
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] in ["assistant", "ai", "system"]:
            messages.append(AIMessage(content=msg["content"]))
            
    messages.append(HumanMessage(content=request.message))
    
    state: IncidentState = {
        "service_name": request.service_name,
        "trace_id": None,
        "timestamp": None,
        "messages": messages,
        "retrieved_logs": None,
        "rca": None
    }
    
    async def event_generator():
        try:
            async for event in graph.astream_events(state, version="v1"):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.error(f"Error in graph streaming: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
