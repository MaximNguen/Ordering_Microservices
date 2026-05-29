from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class TopicConfig:
    name: str
    partitions: int = 3
    replication_factor: int = 2
    retention_ms: Optional[int] = None
    cleanup_policy: str = "delete"
    
    
TOPICS_CONFIG: List[TopicConfig] = [
    TopicConfig("order.created", partitions=6, retention_ms=604800000),
    TopicConfig("order.updated", partitions=3, retention_ms=604800000),
    TopicConfig("delivery.created", partitions=3, retention_ms=604800000),
    TopicConfig("delivery.updated", partitions=3, retention_ms=604800000),
    TopicConfig("delivery.completed", partitions=3, retention_ms=604800000),
    TopicConfig("payment.processed", partitions=3, retention_ms=604800000),
    TopicConfig("dead-letter-queue", partitions=1, retention_ms=2592000000),
    TopicConfig("retry-1s", partitions=1, retention_ms=3600000),
    TopicConfig("retry-5s", partitions=1, retention_ms=3600000),
    TopicConfig("retry-30s", partitions=1, retention_ms=3600000),
]