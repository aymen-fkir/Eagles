from mqtt_client import MQTTService
from kafka_producer import KafkaService
import json
import logging

def message_bridge(client, userdata, msg):
    kafka_service: KafkaService = userdata["kafka_service"]
    try:
        # 1. Parse incoming MQTT data
        payload = json.loads(msg.payload.decode())
        
        # 2. Add metadata (optional but recommended)
        payload["mqtt_topic"] = msg.topic
        
        # 3. Hand over to Kafka
        kafka_service.send_sensor_data(msg.topic, payload)
        logging.info(f"Bridged {msg.topic} to Kafka")
        
    except Exception as e:
        logging.error(f"Error bridging message: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Start the MQTT service with the bridge callback
    mqtt_svc = MQTTService(on_message_callback=message_bridge)
    mqtt_svc.client.user_data_set({"kafka_service": KafkaService()})
    mqtt_svc.run()