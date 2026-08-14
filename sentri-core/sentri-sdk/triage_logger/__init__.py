import asyncio
import json
from datetime import datetime, timezone
import uuid

class SentriLogger:
    """
    A lightweight asynchronous logger SDK for dispatching events to Sentri's Triage Engine via Kafka.
    """
    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "logs-topic"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer = None
        
    async def start(self):
        try:
            from aiokafka import AIOKafkaProducer
        except ImportError:
            raise ImportError("Please install aiokafka to use SentriLogger: pip install aiokafka")
            
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()
        
    async def stop(self):
        if self.producer:
            await self.producer.stop()
            
    async def log(self, service_name: str, severity: str, message: str, owner: str = "unassigned", trace_id: str = None):
        """
        Send a log event to Sentri.
        """
        if not self.producer:
            raise RuntimeError("SentriLogger is not started. Call await logger.start() first.")
            
        if trace_id is None:
            trace_id = f"trace-{uuid.uuid4().hex[:8]}"
            
        log_event = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "service_name": service_name,
            "severity": severity,
            "message": message,
            "trace_id": trace_id,
            "owner": owner
        }
        
        # Sentri expects the payload wrapped in _source
        payload = {"_source": log_event}
        await self.producer.send_and_wait(self.topic, json.dumps(payload).encode("utf-8"))
