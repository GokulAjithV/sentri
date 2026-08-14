# Setting Up Sentri

Welcome to Sentri! This guide will walk you through setting up Sentri on your local machine or server.

## Prerequisites
- Docker and Docker Compose installed
- A running Kafka broker (or Confluent Cloud account)
- A running OpenSearch cluster (or AWS OpenSearch domain)
- A Gemini (Google AI Studio) or OpenAI API key
- A GitHub Personal Access Token (classic, repo-scoped)

## 1. Clone the Repositories
Because Sentri's frontend and backend are maintained as separate repositories, you'll need to clone both into the same parent directory:

```bash
mkdir sentri && cd sentri

# Clone the backend
git clone https://github.com/GokulAjithV/sentri-core.git

# Clone the frontend client
git clone https://github.com/GokulAjithV/sentri-client.git

# Navigate into the core backend to start the setup
cd sentri-core
```

## 2. Configure Environment Variables
Sentri relies heavily on environment variables to connect to your existing infrastructure.
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in your editor and fill out the required credentials:
   - `KAFKA_BOOTSTRAP_SERVERS` & `KAFKA_TOPIC`
   - `OPENSEARCH_ENDPOINT` & credentials
   - `LLM_PROVIDER` and `LLM_API_KEY` (e.g. Gemini)
   - `GITHUB_TOKEN` and `GITHUB_REPO_URLS` (comma-separated links to your repos)
   - `SLACK_WEBHOOK_URL` (optional, for alerts)

## 3. Run the Stack
Run the `docker-compose` stack from inside the `sentri-core` directory. It will automatically build and spin up both the backend and frontend.

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
cd sentri-sdk
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
