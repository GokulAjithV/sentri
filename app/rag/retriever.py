import logging
from typing import List, Dict, Any, Optional
from opensearchpy import OpenSearch

from app.core.config import settings
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_opensearch_client() -> Optional[OpenSearch]:
    """Initialize OpenSearch client."""
    if not settings.OPENSEARCH_ENDPOINT:
        return None
        
    auth = None
    if settings.OPENSEARCH_USERNAME and settings.OPENSEARCH_PASSWORD:
        auth = (settings.OPENSEARCH_USERNAME, settings.OPENSEARCH_PASSWORD)
        
    client = OpenSearch(
        hosts=[settings.OPENSEARCH_ENDPOINT],
        http_auth=auth,
        use_ssl=True if "https" in settings.OPENSEARCH_ENDPOINT else False,
        verify_certs=False,
        ssl_show_warn=False
    )
    return client

def fetch_incident_logs(service_name: str, trace_id: Optional[str] = None, timestamp: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch logs from OpenSearch related to the incident.
    If trace_id is provided, fetches all logs with that trace_id.
    """
    client = get_opensearch_client()
    if not client:
        logger.warning("OpenSearch client not configured. Skipping log retrieval.")
        return []

    # Typically the index would be something like 'crease-app-logs-*' or 'logstash-*'
    # We fetch this from settings:
    index_name = settings.OPENSEARCH_INDEX_PATTERN
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"service_name": service_name}}
                ]
            }
        },
        "sort": [{"timestamp": {"order": "asc"}}],
        "size": 50 # Limit to 50 logs for context window safety
    }
    
    if trace_id:
        query["query"]["bool"]["must"].append({"match": {"trace_id": trace_id}})
    else:
        # If no trace_id, we could fallback to a time range query around the timestamp
        # For simplicity in this demo, we just get recent logs for the service
        logger.warning(f"No trace_id provided for {service_name}, fetching recent logs.")

    try:
        response = client.search(body=query, index=index_name)
        hits = response.get("hits", {}).get("hits", [])
        
        # Extract the actual log payload
        logs = []
        for hit in hits:
            source = hit.get("_source", {})
            # Unwrap nested _source if present (from kafka ingestion plugin)
            if "_source" in source:
                source = source["_source"]
            logs.append(source)
            
        logger.info(f"Retrieved {len(logs)} logs from OpenSearch for trace_id={trace_id}")
        return logs
    except Exception as e:
        logger.error(f"Failed to fetch logs from OpenSearch: {e}")
        return []
