import os
from typing import Optional

class KafkaConfig:
    """Переменные окружения для настройки подключения к Kafka"""
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "delivery-service-group")
    
    KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
    KAFKA_ENABLE_AUTO_COMMIT = os.getenv("KAFKA_ENABLE_AUTO_COMMIT", "False").lower() == "true"
    KAFKA_MAX_POLL_RECORDS = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "500"))
    KAFKA_SESSION_TIMEOUT_MS = int(os.getenv("KAFKA_SESSION_TIMEOUT_MS", "30000"))
    
    KAFKA_ACKS = os.getenv("KAFKA_ACKS", "all")
    KAFKA_RETRIES = int(os.getenv("KAFKA_RETRIES", "3"))
    KAFKA_MAX_IN_FLIGHT = int(os.getenv("KAFKA_MAX_IN_FLIGHT", "5"))
    
    KAFKA_SECURITY_PROTOCOL = os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT")
    KAFKA_SASL_MECHANISM = os.getenv("KAFKA_SASL_MECHANISM", None)
    KAFKA_SASL_USERNAME = os.getenv("KAFKA_SASL_USERNAME", None)
    KAFKA_SASL_PASSWORD = os.getenv("KAFKA_SASL_PASSWORD", None)

    TOPIC_PRODUCT_CREATED = "product.created"
    TOPIC_PRODUCT_UPDATED = "product.updated"
    TOPIC_ORDER_CREATED = "order.created"
    TOPIC_ORDER_UPDATED = "order.updated"
    TOPIC_DELIVERY_CREATED = "delivery.created"
    TOPIC_DELIVERY_UPDATED = "delivery.updated"
    TOPIC_DELIVERY_COMPLETED = "delivery.completed"
    TOPIC_PAYMENT_PROCESSED = "payment.processed"
    
    TOPIC_DLQ = "dead-letter-queue"
    TOPIC_RETRY_1 = "retry-1s"
    TOPIC_RETRY_5 = "retry-5s"
    TOPIC_RETRY_30 = "retry-30s"
    
kafka_config = KafkaConfig()