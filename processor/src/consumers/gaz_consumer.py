import hashlib
import json
import logging
import os
from confluent_kafka import Consumer, KafkaError
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from logger import setup_logger

setup_logger()
log = logging.getLogger("mqtt_bridge.consumer.gaz")

KAFKA_TOPIC    = "factory.line1.telemetry.gaz"
CONSUMER_GROUP = "influx-gaz-consumer"


# ── SHA-256 verification ─────────────────────────────────────────────────────

def compute_signature(payload: dict) -> str:
    """
    Recomputes the SHA-256 over the inner payload fields (canonical JSON).
    Must match exactly how your ESP32 computes the signature.
    """
    inner = {
        "timestamp": payload.get("timestamp"),
        "site_id":   payload.get("site_id"),
        "metric":    payload.get("metric"),
        "value":     payload.get("value"),
    }
    canonical = json.dumps(inner, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def verify_signature(payload: dict) -> bool:
    expected = payload.get("sha256_signature", "")
    computed = compute_signature(payload)
    if expected != computed:
        log.warning(
            f"Signature MISMATCH | expected={expected} | computed={computed} "
            f"| topic={payload.get('mqtt_topic')}"
        )
        return False
    log.debug(f"Signature OK | topic={payload.get('mqtt_topic')}")
    return True


# ── InfluxDB writer ──────────────────────────────────────────────────────────

def write_gaz_to_influx(write_api, payload: dict):
    point = (
        Point("gaz_telemetry")
        .tag("site_id",    payload.get("site_id", "unknown"))
        .tag("metric",     payload.get("metric",  "voc_gas_raw"))
        .tag("mqtt_topic", payload.get("mqtt_topic", ""))
        .field("value", float(payload["value"]))
        .time(payload["timestamp"], WritePrecision.S)
    )
    write_api.write(
        bucket=os.getenv("INFLUX_BUCKET", "iot_factory"),
        org=os.getenv("INFLUX_ORG", "myorg"),
        record=point,
    )
    log.info(
        f"InfluxDB WRITE | measurement=gaz_telemetry "
        f"| site={payload.get('site_id')} | value={payload.get('value')}"
    )


# ── Main consumer loop ───────────────────────────────────────────────────────

def run():
    consumer = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        "group.id":          CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
    })
    consumer.subscribe([KAFKA_TOPIC])
    log.info(f"Gaz consumer started | topic={KAFKA_TOPIC}")

    influx = InfluxDBClient(
        url=os.getenv("INFLUX_URL", "http://localhost:8086"),
        token=os.getenv("INFLUX_TOKEN", ""),
        org=os.getenv("INFLUX_ORG", "myorg"),
    )
    write_api = influx.write_api(write_options=SYNCHRONOUS)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF: #type: ignore
                    log.error(f"Kafka error: {msg.error()}")
                continue

            try:
                payload = json.loads(msg.value().decode("utf-8"))#type: ignore
                log.info(
                    f"CONSUMED | topic={msg.topic()} "
                    f"| metric={payload.get('metric')} | value={payload.get('value')}"
                )

                if not verify_signature(payload):
                    log.warning("Message dropped — signature invalid")
                    continue

                write_gaz_to_influx(write_api, payload)

            except Exception as e:
                log.exception(f"Error processing gaz message: {e}")

    except KeyboardInterrupt:
        log.info("Gaz consumer shutting down")
    finally:
        consumer.close()
        influx.close()


if __name__ == "__main__":
    run()