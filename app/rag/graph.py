import logging
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from typing import Any, cast

from app.core.config import settings
from app.rag.state import IncidentState, RCAResult
from app.rag.retriever import fetch_incident_logs

logger = logging.getLogger(__name__)

def get_llm(temperature: float = 0.0, streaming: bool = False):
    """Factory to initialize the configured LLM provider."""
    provider = settings.LLM_PROVIDER.lower()
    model_name = settings.LLM_MODEL_NAME
    api_key = settings.LLM_API_KEY
    if not api_key:
        raise ValueError("LLM_API_KEY is not set.")
        
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=model_name, api_key=api_key, temperature=temperature, streaming=streaming)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model_name, api_key=api_key, temperature=temperature, streaming=streaming)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=temperature, streaming=streaming)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def retrieve_logs_node(state: IncidentState) -> IncidentState:
    """Retrieve logs for the given trace_id and service_name."""
    logger.info(f"Retrieving logs for {state['service_name']} (trace_id: {state.get('trace_id')})")
    logs = fetch_incident_logs(
        service_name=state["service_name"],
        trace_id=state.get("trace_id"),
        timestamp=state.get("timestamp")
    )
    return {"retrieved_logs": logs}

async def reason_rca_node(state: IncidentState) -> IncidentState:
    """Reason over the retrieved logs and generate the RCA."""
    logger.info("Generating Root Cause Analysis (RCA)")
    
    api_key = settings.LLM_API_KEY
    if not api_key:
        logger.warning("LLM_API_KEY is not set. Skipping RCA generation.")
        return {"rca": None, "messages": [AIMessage(content="LLM_API_KEY is not configured. RCA disabled.")]}
        
    try:
        llm = get_llm(temperature=0.0)
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        return {"rca": None, "messages": [AIMessage(content=f"LLM Configuration Error: {e}")]}
    
    structured_llm = llm.with_structured_output(RCAResult)
    
    logs = state.get("retrieved_logs") or []
    log_text = "\n".join([str(log) for log in logs])
    if not log_text:
        log_text = "No related logs found."
        
    prompt = f"""
    You are Sentri, an expert DevOps AI agent.
    Analyze the following logs for the service '{state['service_name']}' and determine the root cause of the incident.
    
    Logs:
    {log_text}
    """
    
    raw_result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
    
    if not raw_result:
        logger.error("LLM failed to return structured RCA output.")
        fallback_msg = "Could not generate a structured RCA. Ensure logs are available and valid."
        return {
            "rca": None,
            "messages": [AIMessage(content=fallback_msg)]
        }
        
    result = cast(RCAResult, raw_result)
    
    # We inject the structured RCA directly into the message history as an AIMessage 
    # so the frontend can parse it if it wants, but we also return the structured object.
    summary_msg = f"**Hypothesis:** {result.hypothesis}\n\n**Confidence:** {result.confidence_score}%\n\n**Fix:** {result.suggested_fix}"
    
    return {
        "rca": result,
        "messages": [AIMessage(content=summary_msg)]
    }

async def chat_node(state: IncidentState) -> IncidentState:
    """Handle follow-up questions from the user via standard chat."""
    api_key = settings.LLM_API_KEY
    if not api_key:
        return {"messages": [AIMessage(content="LLM_API_KEY is not configured.")]}
        
    try:
        llm = get_llm(temperature=0.3, streaming=True)
    except Exception as e:
        return {"messages": [AIMessage(content=f"LLM Configuration Error: {e}")]}
    
    logs = state.get("retrieved_logs") or []
    log_text = "\n".join([str(log) for log in logs])
    system_prompt = f"""
    You are Sentri, an expert DevOps AI agent. 
    You are assisting a developer in troubleshooting an incident in '{state['service_name']}'.
    
    Relevant Logs:
    {log_text}
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    
    # Returning the final LLM response. (Streaming will be handled by the API endpoint orchestrating the graph)
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

def route_request(state: IncidentState) -> Literal["retrieve_logs_node", "chat_node"]:
    """Determine if this is the initial RCA request or a follow-up chat."""
    if state.get("retrieved_logs") is None:
        return "retrieve_logs_node"
    return "chat_node"

def build_graph() -> CompiledStateGraph:
    workflow = StateGraph(IncidentState)
    
    workflow.add_node("retrieve_logs_node", retrieve_logs_node)
    workflow.add_node("reason_rca_node", reason_rca_node)
    workflow.add_node("chat_node", chat_node)
    
    workflow.add_conditional_edges(START, route_request)
    workflow.add_edge("retrieve_logs_node", "reason_rca_node")
    workflow.add_edge("reason_rca_node", END)
    workflow.add_edge("chat_node", END)
    
    return workflow.compile()
