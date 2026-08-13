from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging

from app.engine.consumer import start_consumer, stop_consumer
from app.core.config import settings
from app.rag.embedder import initialize_codebase_if_empty
from app.api.chat import router as chat_router
from app.api.webhook import router as webhook_router

import logging

# Suppress Kafka internal infinite reconnect logging spam
logging.getLogger("aiokafka").setLevel(logging.CRITICAL)
logging.getLogger("kafka").setLevel(logging.CRITICAL)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sentri Core API",
    description="AI-Powered Log Triage & Root Cause Analysis Platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(webhook_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Sentri Core...")
    
    if not settings.OPENSEARCH_ENDPOINT:
        logger.warning("[CONFIG] OPENSEARCH_ENDPOINT is missing. Log retrieval for RCA will fail.")
    if not settings.LLM_API_KEY:
        logger.warning("[CONFIG] LLM_API_KEY is missing. AI reasoning will fail.")
    if not settings.GITHUB_TOKEN:
        logger.warning("[CONFIG] GITHUB_TOKEN is missing. Code context retrieval will fail.")
    if not settings.SLACK_WEBHOOK_URL:
        logger.warning("[CONFIG] SLACK_WEBHOOK_URL is missing. Alerts will only be logged to the console (Slack Simulation).")
        
    asyncio.create_task(start_consumer())
    asyncio.create_task(initialize_codebase_if_empty())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Sentri Core...")
    await stop_consumer()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    # Permanently configure the port to 8001 when run via `python -m app.main`
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)
