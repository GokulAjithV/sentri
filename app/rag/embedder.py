import os
import zipfile
import tempfile
import httpx
import logging
import asyncio
from pathlib import Path
from urllib.parse import urlparse

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from app.core.config import settings
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Basic extensions we consider as "code" files
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".c", ".cpp", ".h", ".hpp",
    ".rs", ".rb", ".php", ".cs", ".sql", ".sh", ".yaml", ".yml", ".json", ".md"
}

def extract_repo_name(url: str) -> str:
    """Extract the repo name from a GitHub URL (e.g. org/repo-name -> repo-name)."""
    # e.g., https://github.com/org/crease-brain
    path = urlparse(url).path.strip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        return parts[1]
    return path

async def download_github_repo(repo_url: str, token: str, extract_dir: str):
    """Download the repo's default branch zipball and extract it."""
    # Convert https://github.com/org/repo to https://api.github.com/repos/org/repo/zipball
    parsed_url = urlparse(repo_url)
    path = parsed_url.path.strip('/')
    api_url = f"https://api.github.com/repos/{path}/zipball"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Sentri-Triage-Agent"
    }
    
    logger.info(f"Downloading repo from {api_url}")
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(api_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to download repo {repo_url}: {response.status_code} {response.text}")
            
        zip_path = os.path.join(extract_dir, "repo.zip")
        with open(zip_path, "wb") as f:
            f.write(response.content)
            
        logger.info("Extracting repository zip...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
        os.remove(zip_path)
        # GitHub zipballs extract to a folder like `org-repo-commithash`.
        # We find the one created directory.
        extracted_dirs = [os.path.join(extract_dir, d) for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
        if not extracted_dirs:
            raise Exception("Failed to find extracted repository directory.")
        return extracted_dirs[0]

def chunk_code_files(repo_path: str, service_name: str, repo_url: str) -> list[Document]:
    """Walk through the extracted repo, read code files, and chunk them."""
    docs = []
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    # Simple exclude lists
    exclude_dirs = {".git", "node_modules", "venv", "__pycache__", "build", "dist", ".next"}
    
    for root, dirs, files in os.walk(repo_path):
        # Filter excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in CODE_EXTENSIONS:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        
                    # Calculate a permalink for GitHub
                    # In a real app we might fetch the default branch name. Here we use 'main'.
                    github_permalink = f"{repo_url}/blob/main/{rel_path}"
                        
                    metadata = {
                        "service_name": service_name,
                        "file_path": rel_path,
                        "github_permalink": github_permalink
                    }
                    
                    chunks = text_splitter.create_documents([content], [metadata])
                    docs.extend(chunks)
                except Exception as e:
                    logger.debug(f"Skipping file {rel_path} due to read error: {e}")
                    
    return docs

async def embed_all_repos():
    """Fetch and embed all repos configured in GITHUB_REPO_URLS."""
    if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO_URLS:
        logger.warning("GitHub token or repo URLs not configured. Skipping code embedding.")
        return
        
    repo_urls = [r.strip() for r in settings.GITHUB_REPO_URLS.split(",") if r.strip()]
    vector_store = get_vector_store()
    
    for repo_url in repo_urls:
        service_name = extract_repo_name(repo_url)
        logger.info(f"Starting code ingestion for service: {service_name} from {repo_url}")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                repo_path = await download_github_repo(repo_url, settings.GITHUB_TOKEN, temp_dir)
                logger.info(f"Chunking files for {service_name}...")
                docs = chunk_code_files(repo_path, service_name, repo_url)
                
                if docs:
                    logger.info(f"Adding {len(docs)} chunks to ChromaDB for {service_name}...")
                    # We might want to clear old vectors for this service_name first, 
                    # but for simplicity we'll just add. Chroma handles dupes if IDs match, 
                    # but we are generating new UUIDs. A real implementation would delete based on filter.
                    vector_store.add_documents(docs)
                    logger.info(f"Successfully embedded {service_name}.")
                else:
                    logger.warning(f"No code chunks generated for {service_name}.")
            except Exception as e:
                logger.error(f"Failed to ingest {repo_url}: {e}")

async def initialize_codebase_if_empty():
    """Check if ChromaDB is empty on startup, and trigger embedding if so."""
    if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO_URLS:
        return
        
    try:
        vector_store = get_vector_store()
        count = vector_store._collection.count()
        if count == 0:
            logger.info("ChromaDB vector store is empty. Triggering initial codebase embedding...")
            await embed_all_repos()
        else:
            logger.info(f"ChromaDB already contains {count} code chunks. Skipping initial embedding.")
    except Exception as e:
        logger.error(f"Failed to check or initialize vector store: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(embed_all_repos())
