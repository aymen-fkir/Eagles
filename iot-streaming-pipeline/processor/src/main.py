import logging
import threading
import sys
import os

# Add src to path so imports work inside Docker
sys.path.insert(0, os.path.dirname(__file__))

from logger import setup_logger
from consumers.gaz_consumer import run as run_gaz
from consumers.valve_consumer import run as run_valve

setup_logger()
log = logging.getLogger("mqtt_bridge.consumers.main")


def start_consumer(name: str, target):
    """Wraps a consumer run() in a daemon thread with error logging."""
    def wrapper():
        try:
            log.info(f"Starting consumer: {name}")
            target()
        except Exception as e:
            log.exception(f"Consumer '{name}' crashed: {e}")

    t = threading.Thread(target=wrapper, name=name, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    log.info("═" * 60)
    log.info("IoT Kafka → InfluxDB consumers starting")
    log.info("═" * 60)

    threads = [
        start_consumer("gaz-consumer",   run_gaz),
        start_consumer("valve-consumer", run_valve),
    ]

    # Block main thread — keep process alive as long as threads run
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log.info("Shutdown signal received — stopping consumers")