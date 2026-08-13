from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel
import logging

from app.rag.embedder import embed_all_repos

logger = logging.getLogger(__name__)

router = APIRouter()

class WebhookResponse(BaseModel):
    message: str

@router.post("/webhook/github", response_model=WebhookResponse)
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Webhook to trigger codebase re-embedding.
    For simplicity, this just accepts a POST and re-embeds all configured repos.
    In a production setup, it would parse the payload and embed only the changed repo.
    """
    logger.info("Received GitHub push webhook. Triggering background embed job.")
    background_tasks.add_task(embed_all_repos)
    return {"message": "Embedding job started in background"}
