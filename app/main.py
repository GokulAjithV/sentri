from fastapi import FastAPI
import asyncio
import logging

from app.engine.consumer import start_consumer, stop_consumer
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sentri Core API",
    description="AI-Powered Log Triage & Root Cause Analysis Platform",
    version="1.0.0"
)

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

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Sentri Core...")
    await stop_consumer()

@app.get("/health")
def health_check():
    return {"status": "healthy"}
