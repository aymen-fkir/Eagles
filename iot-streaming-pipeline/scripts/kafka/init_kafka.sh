#!/bin/bash

BOOTSTRAP_SERVER="kafka:9092"
PARTITIONS=4
REPLICATION_FACTOR=1
PREFIX="factory.line1.telemetry"
TOPICS=("$PREFIX.valve" "$PREFIX.gaz" "$PREFIX.general")

echo "⏳ Waiting for Kafka to be ready at $BOOTSTRAP_SERVER..."
until /opt/kafka/bin/kafka-broker-api-versions.sh \
  --bootstrap-server $BOOTSTRAP_SERVER > /dev/null 2>&1; do
  echo "  - Kafka is unreachable. Retrying in 2s..."
  sleep 2
done

echo "✅ Kafka is up! Proceeding with topic creation..."

for TOPIC in "${TOPICS[@]}"; do
  /opt/kafka/bin/kafka-topics.sh --create --if-not-exists \
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

echo "🚀 Kafka initialization complete!""