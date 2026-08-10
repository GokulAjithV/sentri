import asyncio
import json
import logging
from typing import Optional
from aiokafka import AIOKafkaConsumer
from app.core.config import settings
from app.engine.triage import process_log_event

logger = logging.getLogger(__name__)

# Global consumer instance
_consumer: Optional[AIOKafkaConsumer] = None
_consume_task: Optional[asyncio.Task] = None

async def start_consumer():
    global _consumer, _consume_task
    
    logger.info(f"Connecting to Kafka brokers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    
    # Simple retry loop for Kafka connection
    max_retries = 5
    for attempt in range(max_retries):
        try:
            _consumer = AIOKafkaConsumer(
                settings.KAFKA_TOPIC,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id="sentri-triage-group",
                auto_offset_reset="latest" # Or "earliest" for testing
            )
            await _consumer.start()
            logger.info("Successfully connected to Kafka.")
            break
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka (attempt {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
            else:
                logger.error("Could not connect to Kafka after multiple attempts.")
                return

    _consume_task = asyncio.create_task(consume_loop())

async def consume_loop():
    logger.info("Starting Triage Engine consume loop...")
    
    if _consumer is None:
        logger.error("Consumer is not initialized.")
        return
        
    try:
        async for msg in _consumer:
            logger.debug(f"Received raw message: {msg.value}")
            if msg.value is None:
                continue
            try:
                log_data = json.loads(msg.value.decode("utf-8"))
                process_log_event(log_data)
            except json.JSONDecodeError:
                logger.error("Failed to decode Kafka message as JSON")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
    except asyncio.CancelledError:
        logger.info("Consume loop cancelled.")
    except Exception as e:
        logger.error(f"Unexpected error in consume loop: {e}")

async def stop_consumer():
    global _consumer, _consume_task
    if _consume_task:
        _consume_task.cancel()
        try:
            await _consume_task
        except asyncio.CancelledError:
            pass
    if _consumer:
        await _consumer.stop()
        logger.info("Kafka consumer stopped.")
