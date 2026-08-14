import logging
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from typing import Any, cast
from pydantic import BaseModel, Field

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

def retrieve_code_node(state: IncidentState) -> IncidentState:
    """Retrieve code snippets from ChromaDB based on the error log."""
    logger.info(f"Retrieving code for {state['service_name']}")
    logs = state.get("retrieved_logs", [])
    messages = state.get("messages", [])
    
    query = ""
    if logs:
        # Use the first log's message as the query for incidents
        query = logs[0].get("message", "")
    elif messages:
        # If no logs but we have chat messages (Explore mode), use the latest message
        query = str(messages[-1].content)
        
    if not query:
        logger.warning("No logs and no messages to base code search on.")
        return {"retrieved_code": []}
    
    try:
        from app.rag.vector_store import get_vector_store
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(
            query=query,
            k=3,
            filter={"service_name": state["service_name"]}
        )
        code_snippets = []
        for d in docs:
            snippet = f"File: {d.metadata.get('file_path')} (Permalink: {d.metadata.get('github_permalink')})\n{d.page_content}"
            code_snippets.append(snippet)
        return {"retrieved_code": code_snippets}
    except Exception as e:
        logger.error(f"Failed to retrieve code: {e}")
        return {"retrieved_code": []}

class GradeResult(BaseModel):
    is_sufficient: bool = Field(description="True if context is sufficient to diagnose, False otherwise")
    score: int = Field(description="Score from 0 to 100")

async def grade_context_node(state: IncidentState) -> IncidentState:
    """Grade the retrieved context."""
    logger.info("Grading retrieved context")
    try:
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(GradeResult)
        
        logs = state.get("retrieved_logs") or []
        code = state.get("retrieved_code") or []
        
        prompt = f"""
        Evaluate if the following context is sufficient to root cause an error in {state['service_name']}.
        Logs: {logs}
        Code: {code}
        """
        raw_result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
        if raw_result:
            result = cast(GradeResult, raw_result)
            return {"context_score": result.score}
        return {"context_score": 100}
    except Exception as e:
        logger.warning(f"Grading failed: {e}")
        return {"context_score": 100}

async def reason_rca_node(state: IncidentState) -> IncidentState:
    """Reason over the retrieved logs and code to generate the RCA."""
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
    code = state.get("retrieved_code") or []
    
    log_text = "\n".join([str(log) for log in logs]) or "No related logs found."
    code_text = "\n\n".join(code) or "No related code found."
        
    prompt = f"""
    You are Sentri, an expert DevOps AI agent.
    Analyze the following logs and code snippets for the service '{state['service_name']}' to determine the root cause.
    
    Logs:
    {log_text}
    
    Code Snippets:
    {code_text}
    
    If you identify the buggy file, populate the github_permalink field.
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
    
    # We inject the structured RCA directly into the message history
    summary_msg = f"**Hypothesis:** {result.hypothesis}\n\n**Confidence:** {result.confidence_score}%\n\n**Fix:** {result.suggested_fix}"
    if result.github_permalink:
        summary_msg += f"\n\n**Blame:** [View File on GitHub]({result.github_permalink})"
    
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
    code = state.get("retrieved_code") or []
    log_text = "\n".join([str(log) for log in logs])
    code_text = "\n\n".join(code)
    
    system_prompt = f"""
    You are Sentri, an expert DevOps AI agent. 
    You are assisting a developer in troubleshooting an incident in '{state['service_name']}'.
    
    Relevant Logs:
    {log_text}
    
    Relevant Code:
    {code_text}
    """
    
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

def route_after_retrieval(state: IncidentState) -> Literal["grade_context_node", "chat_node"]:
    """Determine if this is the initial RCA request or a follow-up chat after retrieving context."""
    if len(state.get("messages", [])) > 0:
        return "chat_node"
    return "grade_context_node"

def build_graph() -> CompiledStateGraph:
    workflow = StateGraph(IncidentState) # type: ignore
    
    workflow.add_node("retrieve_logs_node", retrieve_logs_node)
    workflow.add_node("retrieve_code_node", retrieve_code_node)
    workflow.add_node("grade_context_node", grade_context_node)
    workflow.add_node("reason_rca_node", reason_rca_node)
    workflow.add_node("chat_node", chat_node)
    
    workflow.add_edge(START, "retrieve_logs_node")
    workflow.add_edge("retrieve_logs_node", "retrieve_code_node")
    workflow.add_conditional_edges("retrieve_code_node", route_after_retrieval)
    
    workflow.add_edge("grade_context_node", "reason_rca_node")
    workflow.add_edge("reason_rca_node", END)
    workflow.add_edge("chat_node", END)
    
    return workflow.compile()
