from prometheus_client import Counter, Histogram, Gauge

delivery_created_counter = Counter(
    'delivery_created_total', 
    'Total number of deliveries created',
    ['status']
)

delivery_updated_counter = Counter(
    'delivery_updated_total',
    'Total number of deliveries updated',
    ['field']
)

delivery_delete_counter = Counter(
    'delivery_deleted_total',
    'Total number of deliveries deleted'
)

# Kafka метрики
kafka_messages_received = Counter(
    'kafka_messages_received_total',
    'Total Kafka messages received',
    ['event_type', 'topic']
)

kafka_processing_time = Histogram(
    'kafka_message_processing_seconds',
    'Time spent processing Kafka messages',
    ['event_type'],
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0)
)

# БД метрики
db_query_duration = Histogram(
    'db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)

# Gauge метрики
active_deliveries_gauge = Gauge(
    'active_deliveries_count',
    'Current number of active deliveries'
)