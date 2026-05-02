from confluent_kafka import Producer
import json
import os

class KafkaService:
    def __init__(self):
        self.producer = Producer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Ensure delivery: wait for all replicas to acknowledge
            acks='all'
        )

    def send_sensor_data(self, mqtt_topic, payload):
        """
        Logic to route MQTT topics to Kafka topics.
        Example: 'sensors/alpha/temp' -> Topic: 'sensor.group.alpha'
        """
        parts = mqtt_topic.split('/')
        
        # Routing Logic
        if len(parts) >= 2:
            group_name = parts[1] # e.g., 'alpha'
            kafka_topic = f"sensor.group.{group_name}"
        else:
            kafka_topic = "sensor.general"

        # USE SENSOR_ID AS KEY
        # This ensures all data from one sensor stays in the same partition (order)
        sensor_id = payload.get("sensor_id", "unknown")
        
        self.producer.produce(
            kafka_topic, 
            value=payload,
            key=sensor_id.encode('utf-8') 
        )