import os
import logging
from typing import Optional
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma

from app.core.config import settings

logger = logging.getLogger(__name__)

# Base directory for Chroma persistence
CHROMA_PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".chroma_db")

def get_embeddings():
    """Initialize the embedding model based on LLM provider."""
    provider = settings.LLM_PROVIDER.lower()
    
    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        api_key = settings.LLM_API_KEY
        if not api_key:
            raise ValueError("LLM_API_KEY is not set for OpenAI Embeddings.")
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
        
    elif provider == "gemini":
        # Gemini free-tier has a strict 100 requests/min limit, which fails for bulk code ingestion.
        # We fall back to FastEmbed (local ONNX) to embed the codebase instantly without quota limits.
        try:
            # Route all model downloads to the local workspace on V drive instead of C drive
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".model_cache")
            os.environ["HF_HOME"] = os.path.join(cache_dir, "huggingface")
            
            from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
            return FastEmbedEmbeddings(
                model_name="BAAI/bge-small-en-v1.5", 
                cache_dir=os.path.join(cache_dir, "fastembed")
            )
        except ImportError:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            api_key = settings.LLM_API_KEY
            if not api_key:
                raise ValueError("LLM_API_KEY is not set for Google Embeddings.")
            return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2", google_api_key=api_key)
        
    elif provider == "anthropic":
        # Anthropic doesn't have native embeddings, default to OpenAI if key provided
        from langchain_openai import OpenAIEmbeddings
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set in .env if using Anthropic for LLM provider.")
        return OpenAIEmbeddings(model="text-embedding-3-small", api_key=api_key)
        
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")

def get_vector_store(collection_name: str = "sentri_codebase") -> Chroma:
    """Initialize and return the Chroma vector store."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    
    client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR, settings=Settings(anonymized_telemetry=False))
    
    try:
        embeddings = get_embeddings()
    except Exception as e:
        logger.error(f"Failed to initialize embeddings: {e}")
        # Return a dummy vector store if embeddings fail, or raise
        raise e
        
    vector_store = Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=embeddings,
    )
    
    return vector_store
