import json
import logging
from logger import setup_logger
from mqtt_client import MQTTService
from kafka_producer import KafkaService

setup_logger()
log = logging.getLogger("mqtt_bridge.main")


def message_bridge(client, userdata, msg):
    kafka_service: KafkaService = userdata["kafka_service"]
    try:
        payload = json.loads(msg.payload.decode())
        payload["mqtt_topic"] = msg.topic

        # ── Log every incoming message to file ───────────────────────────────
        log.info(
            f"RECEIVED | topic={msg.topic} "
            f"| sensor={payload.get('sensor_id', 'unknown')} "
            f"| payload={json.dumps(payload)}"
        )

        kafka_service.send_sensor_data(msg.topic, payload)
        log.info(f"FORWARDED | topic={msg.topic} → Kafka")

    except json.JSONDecodeError as e:
        log.error(f"JSON parse error on topic {msg.topic}: {e} | raw={msg.payload}")
    except Exception as e:
        log.exception(f"Unexpected error bridging {msg.topic}: {e}")


if __name__ == "__main__":
    log.info("═" * 60)
    log.info("MQTT → Kafka bridge starting up")
    log.info("═" * 60)

    kafka_svc = KafkaService()
    mqtt_svc = MQTTService(on_message_callback=message_bridge)
    mqtt_svc.client.user_data_set({"kafka_service": kafka_svc})

    mqtt_svc.run()