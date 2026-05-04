import json
import logging
import os
from confluent_kafka import Producer
from logger import setup_logger

setup_logger()
log = logging.getLogger("mqtt_bridge.kafka")

# ── Topic routing map ────────────────────────────────────────────────────────
TOPIC_ROUTING = {
    "barrage_valve_percent": "factory.line1.telemetry.valve",
    "voc_gas_raw":           "factory.line1.telemetry.gaz",
}
DEFAULT_TOPIC = "factory.line1.telemetry.general"


def resolve_kafka_topic(mqtt_topic: str) -> str:
    """
    Maps an MQTT topic to the correct Kafka topic.

    factory/line1/telemetry/barrage_valve_percent → factory.line1.telemetry.valve
    factory/line1/telemetry/voc_gas_raw           → factory.line1.telemetry.gaz
    """
    metric = mqtt_topic.split("/")[-1]
    kafka_topic = TOPIC_ROUTING.get(metric, DEFAULT_TOPIC)
    log.debug(f"Routing | mqtt={mqtt_topic} → kafka={kafka_topic}")
    return kafka_topic


def parse_payload(raw: dict, mqtt_topic: str) -> dict:
    """
    Flattens the nested payload structure.

    Input:
        {
            "payload": {"timestamp": "...", "site_id": "...", "metric": "...", "value": 85},
            "sha256_signature": "abc123...",
            "mqtt_topic": "factory/line1/telemetry/barrage_valve_percent"
        }

    Output (flat):
        {
            "timestamp":        "2026-05-02 13:49:46",
            "site_id":          "Factory_Line_A",
            "metric":           "barrage_valve_percent",
            "value":            85,
            "sha256_signature": "abc123...",
            "mqtt_topic":       "factory/line1/telemetry/barrage_valve_percent"
        }
    """
    inner  = raw.get("payload", raw)   # support both nested and already-flat
    result = dict(inner)
    result["sha256_signature"] = raw.get("sha256_signature", "")
    result["mqtt_topic"]       = mqtt_topic
    return result


class KafkaService:
    def __init__(self):
        conf = {
            "bootstrap.servers": os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"
            ),
            "acks": "all",
        }
        self.producer = Producer(conf)
        log.info(f"Kafka producer ready → {conf['bootstrap.servers']}")

    def send_sensor_data(self, mqtt_topic: str, raw_payload: dict):
        # 1. Parse and flatten
        payload     = parse_payload(raw_payload, mqtt_topic)
        kafka_topic = resolve_kafka_topic(mqtt_topic)
        sensor_id   = payload.get("sensor_id", payload.get("site_id", "unknown"))

        log.info(
            f"ROUTING | mqtt={mqtt_topic} → kafka={kafka_topic} "
            f"| metric={payload.get('metric')} | value={payload.get('value')}"
        )

        # 2. Produce to correct Kafka topic
        self.producer.produce(
            kafka_topic,
            value=json.dumps(payload).encode("utf-8"),
            key=sensor_id.encode("utf-8"),
            callback=self._delivery_report,
        )
        self.producer.poll(0)

    def _delivery_report(self, err, msg):
        if err:
            log.error(f"Kafka delivery FAILED | topic={msg.topic()} | {err}")
        else:
            log.debug(
                f"Kafka delivery OK | topic={msg.topic()} "
                f"| partition={msg.partition()} | offset={msg.offset()}"
            )