import asyncio
import json
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer

async def send_mock_error():
    producer = AIOKafkaProducer(
        bootstrap_servers='localhost:9092'
    )
    await producer.start()
    try:
        mock_log = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "service_name": "test-server",
            "environment": "staging",
            "severity": "ERROR",
            "message": "Simulated database connection failure (Test 5)",
            "trace_id": "test-trace-124",
            "owner": "team-crease-backend"
        }
        # Wrap it in _source to match what OpenSearch/Logstash provides
        payload = {"_source": mock_log}
        
        await producer.send_and_wait("crease-logs", json.dumps(payload).encode("utf-8"))
        print(f"Sent mock ERROR event: {mock_log['message']}")
        
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(send_mock_error())
