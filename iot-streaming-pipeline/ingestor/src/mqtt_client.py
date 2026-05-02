import os
import logging
import paho.mqtt.client as mqtt
from logger import setup_logger

# Initialise once; all subsequent getLogger() calls share the same handlers
setup_logger()
log = logging.getLogger("mqtt_bridge.mqtt")


class MQTTService:
    def __init__(self, on_message_callback):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = on_message_callback

        self.host = os.getenv("MQTT_HOST", "localhost")
        self.port = int(os.getenv("MQTT_PORT", 1883))

        log.info(f"MQTT broker → {self.host}:{self.port}")

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            log.info("Connected to Mosquitto successfully")
            self.client.subscribe("factory/line1/telemetry/#")
            log.info("Subscribed to factory/line1/telemetry/#")
        else:
            log.error(f"Connection failed with code {rc}")

    def run(self):
        self.client.connect(self.host, self.port, 60)
        self.client.loop_forever()