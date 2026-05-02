# IoT Streaming Pipeline

A modern, containerized IoT data streaming architecture that ingests sensor data from MQTT devices, streams it through Apache Kafka, and stores time-series data in InfluxDB.

## Overview

This project implements an end-to-end IoT platform for collecting, processing, and storing sensor telemetry from industrial devices (gas sensors, valves, etc.) in real-time.

### Key Features

- **MQTT Ingestion**: Receives sensor data from IoT devices via MQTT protocol with SSL/TLS support
- **Kafka Streaming**: Stream processing and decoupling of data producers from consumers using Apache Kafka (KRaft mode)
- **Time-Series Storage**: Stores processed metrics in InfluxDB for analytics and visualization
- **Multi-Consumer Processing**: Parallel consumers for different sensor types (gas, valve, etc.)
- **Data Validation**: SHA-256 payload verification for data integrity
- **Docker-Orchestrated**: Complete containerization with Docker Compose
- **Comprehensive Logging**: Structured logging across all components

## Architecture

```
IoT Devices (MQTT)
    ↓
[Mosquitto MQTT Broker]
    ↓
[Ingestor Service] → JSON parsing & enrichment
    ↓
[Apache Kafka] → Topic-based streaming
    ↓
[Processor Consumers] → Multiple parallel consumers
    ↓
[InfluxDB] → Time-series storage
```

## System Components

### 1. **Mosquitto** (MQTT Broker)
- Eclipse Mosquitto with OpenSSL support
- Handles incoming MQTT connections on port 1883 (plain) and 8883 (TLS)
- Stores messages for reliability
- Configuration: `scripts/mosquitto/mosquitto.conf`

### 2. **Apache Kafka** (Message Broker)
- KRaft mode (no Zookeeper required)
- Decouples sensor data producers from consumers
- Topics: `factory.line1.telemetry.gaz`, `factory.line1.telemetry.valve`
- Bootstrap server: `kafka:9092`

### 3. **Ingestor Service**
- Subscribes to MQTT topics
- Converts sensor payloads to JSON
- Enriches messages with MQTT topic information
- Forwards data to Kafka topics
- Location: `ingestor/src/main.py`

### 4. **Processor Service**
- Multiple consumer threads:
  - **Gaz Consumer**: Processes gas sensor telemetry
  - **Valve Consumer**: Processes valve control data
- SHA-256 payload verification
- Writes validated data to InfluxDB
- Location: `processor/src/consumers/`

### 5. **InfluxDB** (Time-Series Database)
- Stores sensor metrics with timestamps
- Retention policy: 30 days
- 2.7.x with authentication
- Admin UI available on port 8086

## Prerequisites

- Docker & Docker Compose (v2.0+)
- Python 3.12+ (for local development)
- 2GB+ free RAM
- Port availability: 1883, 8883, 9092, 8086

## Quick Start

### 1. Clone and Navigate

```bash
cd /path/to/iot-streaming-pipeline
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
# InfluxDB
INFLUX_USER=admin
INFLUX_PASSWORD=your_secure_password
INFLUX_ORG=myorg
INFLUX_BUCKET=iot_factory
INFLUX_TOKEN=your_secure_token

# MQTT (Optional - for TLS)
MQTT_CERTS_PATH=/path/to/certs
```

### 3. Start Services

```bash
docker compose up -d
```

This will start all services in order:
1. MQTT Broker (Mosquitto)
2. Kafka & Topic Initialization
3. Ingestor Service
4. InfluxDB & Schema Initialization
5. Processor Service

### 4. Verify Services

```bash
# Check container status
docker compose ps

# View logs
docker compose logs -f ingestor
docker compose logs -f processor
```

## Configuration

### MQTT Topics

The ingestor subscribes to MQTT topics matching patterns. Common topics:

```
factory/line1/gas
factory/line1/valve
factory/line1/temperature
```

### Kafka Topics

Automatically created with topics:
- `factory.line1.telemetry.gaz`
- `factory.line1.telemetry.valve`

Configuration: `scripts/kafka/init_kafka.sh`

### InfluxDB Schema

Initial setup script creates buckets and retention policies:
- Location: `scripts/influx/script.sh`
- Default bucket: `iot_factory`
- Retention: 30 days

## Data Flow

### Ingestor Flow

```
MQTT Payload (JSON)
    ↓
[message_bridge callback]
    ↓
Enrichment (add mqtt_topic field)
    ↓
KafkaService.send_sensor_data()
    ↓
Kafka Topic (Based on MQTT topic mapping)
```

### Processor Flow

```
Kafka Consumer
    ↓
[Consumer Thread] (gaz or valve)
    ↓
Payload Verification (SHA-256)
    ↓
Data Validation
    ↓
InfluxDBClient.write_points()
    ↓
InfluxDB Storage
```

## Development

### Project Structure

```
.
├── ingestor/               # MQTT → Kafka bridge
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py
│   │   ├── mqtt_client.py
│   │   ├── kafka_producer.py
│   │   └── logger.py
│
├── processor/              # Kafka → InfluxDB consumers
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py
│   │   ├── logger.py
│   │   └── consumers/
│   │       ├── gaz_consumer.py
│   │       └── valve_consumer.py
│
├── hardware/               # IoT device code
│   └── runner.ino          # Arduino/ESP32 firmware
│
├── scripts/
│   ├── kafka/init_kafka.sh
│   ├── influx/script.sh
│   └── mosquitto/          # MQTT config & certs
│
└── docker-compose.yml      # Orchestration
```

### Local Development Setup

```bash
# Create virtual environment
python3 -m venv ingestor/.venv
source ingestor/.venv/bin/activate

# Install dependencies
pip install -e ingestor/
pip install -e processor/

# Run tests (if available)
pytest
```

### Adding a New Consumer

1. Create `processor/src/consumers/new_consumer.py`
2. Implement `run()` function
3. Add to `processor/src/main.py` in `start_consumer()` calls

Example:

```python
# processor/src/consumers/new_consumer.py
def run():
    consumer = Consumer({
        'bootstrap.servers': os.getenv('KAFKA_BOOTSTRAP_SERVERS'),
        'group.id': 'my-consumer-group',
        'auto.offset.reset': 'earliest'
    })
    consumer.subscribe(['factory.line1.telemetry.new'])
    
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        # Process message
```

## Monitoring & Operations

### View Live Data

```bash
# Check MQTT traffic (inside mosquitto container)
docker exec mosquitto mosquitto_sub -h localhost -t 'factory/#'

# Monitor Kafka topics
docker exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic factory.line1.telemetry.gaz \
  --from-beginning

# Query InfluxDB
curl -X GET http://localhost:8086/api/v2/query \
  -H "Authorization: Token your_token" \
  -d "org=myorg&bucket=iot_factory"
```

### Logs

```bash
# All services
docker compose logs

# Specific service
docker compose logs -f ingestor
docker compose logs -f processor

# With timestamps
docker compose logs --timestamps
```

### Health Checks

Services include health checks:
- **Kafka**: Broker API version check
- **InfluxDB**: HTTP health endpoint

Check status:
```bash
docker compose ps
```

## Troubleshooting

### Ingestor not connecting to MQTT

1. Verify Mosquitto is running: `docker compose logs mosquitto`
2. Check credentials in `.env` if using authentication
3. Verify MQTT_HOST and MQTT_PORT environment variables
4. Check TLS certs if using 8883: `ls scripts/mosquitto/certs/`

### Kafka topics not created

1. Verify kafka-setup service completed: `docker compose logs kafka-setup`
2. Check init script: `scripts/kafka/init_kafka.sh`
3. Ensure Kafka is healthy: `docker compose ps | grep kafka`

### InfluxDB connection errors

1. Verify InfluxDB is running: `docker compose ps influxdb`
2. Check credentials in `.env` match DOCKER_INFLUXDB_INIT_*
3. Verify bucket exists: Check InfluxDB UI on http://localhost:8086
4. Check logs: `docker compose logs influx-setup`

### Memory/Performance Issues

- Reduce consumer group scaling
- Increase Kafka log retention settings
- Check InfluxDB query performance

## Data Format

### MQTT Message Format

```json
{
  "timestamp": 1234567890,
  "site_id": "factory_1",
  "sensor_id": "gaz_001",
  "metric": "CO2_ppm",
  "value": 450.5,
  "unit": "ppm",
  "signature": "sha256_hash"
}
```

### InfluxDB Points

Stored with fields:
- `value` (float)
- `site_id` (tag)
- `sensor_id` (tag)
- `metric` (tag)
- Timestamp: message timestamp

Query example:
```flux
from(bucket:"iot_factory")
  |> range(start: -24h)
  |> filter(fn: (r) => r.metric == "CO2_ppm")
```

## Performance Tuning

### Kafka

- Batch size configuration in `docker-compose.yml`
- Consumer group scaling in `processor/src/consumers/`

### InfluxDB

- Increase shard duration for high-frequency data
- Adjust retention policies based on storage needs

### MQTT

- Connection limits: `max_connections` in mosquitto.conf
- QoS level configuration

## Security Considerations

- Store `.env` securely (add to `.gitignore`)
- Use TLS for MQTT (port 8883) in production
- Rotate InfluxDB tokens regularly
- Restrict network access with firewall rules
- Validate all incoming MQTT payloads (SHA-256 verification enabled)

## Contributing

1. Create feature branches from main
2. Follow existing code structure and logging patterns
3. Add tests for new consumers
4. Update README with new features

## License

[Specify your license]

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Review troubleshooting section above
3. Check service health: `docker compose ps`

---

**Version**: 0.1.0  
**Last Updated**: May 2026  
**Python**: 3.12+  
**Docker Compose**: 2.0+
