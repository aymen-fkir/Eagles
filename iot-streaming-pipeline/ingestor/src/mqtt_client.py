import paho.mqtt.client as mqtt
import os
import logging

class MQTTService:
    def __init__(self, on_message_callback):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = on_message_callback
        self.host = os.getenv("MQTT_BROKER_HOST", "localhost")
        self.port = int(os.getenv("MQTT_BROKER_PORT", 1883))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("connected to Mosquitto successfully")
            # Subscribe to all sensor groups
            self.client.subscribe("sensors/#")
        else:
            logging.error(f"Connection failed with code {rc}")

    def run(self):
        self.client.connect(self.host, self.port, 60)
        self.client.loop_forever()