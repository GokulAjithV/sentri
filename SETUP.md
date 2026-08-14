# Setting Up Sentri

Welcome to Sentri! This guide will walk you through setting up Sentri on your local machine or server.

## Prerequisites
- Docker and Docker Compose installed
- A running Kafka broker (or Confluent Cloud account)
- A running OpenSearch cluster (or AWS OpenSearch domain)
- A Gemini (Google AI Studio) or OpenAI or Anthropic API Key
- A GitHub Personal Access Token (classic, repo-scoped)

## 1. Clone the Repository

```bash
git clone https://github.com/GokulAjithV/sentri.git
cd sentri
```

## 2. Configure Environment Variables
Sentri relies heavily on environment variables to connect to your existing infrastructure.
1. Copy the example environment file:
   ```bash
   cp sentri-core/.env.example sentri-core/.env
   ```
2. Open `sentri-core/.env` in your editor and fill out the required credentials:
   - `KAFKA_BOOTSTRAP_SERVERS` & `KAFKA_TOPIC`
   - `OPENSEARCH_ENDPOINT` & credentials
   - `LLM_PROVIDER` and `LLM_API_KEY` (e.g. Gemini)
   - `GITHUB_TOKEN` and `GITHUB_REPO_URLS` (comma-separated links to your repos)
   - `SLACK_WEBHOOK_URL` (optional, for alerts)

## 3. Run the Stack

You can run Sentri using the pre-built images from Docker Hub, or build them locally from source.

### Option A: Use Pre-built Images (Fastest)
If you don't want to compile the code locally, you can pull the official images directly from Docker Hub:

```bash
# Run the backend
docker run -d -p 8001:8001 --name sentri-core --env-file sentri-core/.env gokulajith/sentri-core:latest

# Run the frontend
docker run -d -p 3001:80 --name sentri-client -e VITE_SENTRI_CORE_API_URL=http://localhost:8001 gokulajith/sentri-client:latest
```

### Option B: Build Locally
Run the `docker-compose` stack from the root directory. It will automatically build and spin up both the backend and frontend from the source code.

```bash
docker-compose up --build -d
```

This will spin up:
- **`sentri-core`** on `http://localhost:8001`
- **`sentri-client`** on `http://localhost:3001`

You can now visit `http://localhost:3001` to view the Explore Codebase UI!

## 4. Integrate Your App
To have your application start sending logs to Sentri, install the lightweight Python SDK located in the core repository:

```bash
cd sentri-core/sentri-sdk
pip install -e .
```

Then use it in your code:

```python
import asyncio
from triage_logger import SentriLogger

async def main():
    logger = SentriLogger(bootstrap_servers="localhost:9092")
    await logger.start()
    
    await logger.log(
        service_name="my-service",
        severity="ERROR",
        message="Database connection failed",
        owner="team-backend"
    )
    await logger.stop()

asyncio.run(main())
```

Once Sentri detects an ERROR or WARN log, it will instantly dispatch a magic link to your Slack or Email!
