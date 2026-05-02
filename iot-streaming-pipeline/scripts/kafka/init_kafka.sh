#!/bin/bash

# Configuration
BOOTSTRAP_SERVER="kafka:9092"
PARTITIONS=4
REPLICATION_FACTOR=1

PREFIX="factory.line1.telemetry"

# List of topics to create
TOPICS=("$PREFIX.valve" "$PREFIX.gaz")

echo "⏳ Waiting for Kafka to be ready at $BOOTSTRAP_SERVER..."

# 'cub kafka-ready' is specific to Confluent images. 
# For a more universal check, we use the kafka-broker-api-versions tool.
until kafka-broker-api-versions --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; do
  echo "  - Kafka is unreachable. Retrying in 2s..."
  sleep 2
done

echo "✅ Kafka is up! Proceeding with topic creation..."

for TOPIC in "${TOPICS[@]}"; do
  kafka-topics --create --if-not-exists \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --partitions $PARTITIONS \
    --replication-factor $REPLICATION_FACTOR \
    --topic "$TOPIC"
  
  if [ $? -eq 0 ]; then
    echo "  + Topic '$TOPIC' created/verified."
  else
    echo "  - Failed to create topic '$TOPIC'."
  fi
done

echo "🚀 Kafka initialization complete!"