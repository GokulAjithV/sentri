from fastapi import FastAPI
import asyncio
import logging

from app.engine.consumer import start_consumer, stop_consumer

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
    asyncio.create_task(start_consumer())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Sentri Core...")
    await stop_consumer()

@app.get("/health")
def health_check():
    return {"status": "healthy"}
