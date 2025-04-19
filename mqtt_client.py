import paho.mqtt.client as mqtt
import json
import logging
import queue
from threading import Thread
import data_processor
import config

# Configure logging
logger = logging.getLogger(__name__)

# Queue for real-time data display (limited to 100 items)
sensor_data_queue = queue.Queue(maxsize=100)

class MQTTClient:
    def __init__(self, broker_host=None, broker_port=None, topic=None):
        """
        Initialize MQTT client
        
        Args:
            broker_host (str): MQTT broker hostname or IP
            broker_port (int): MQTT broker port
            topic (str): MQTT topic to subscribe to
        """
        # Use config values if parameters are not provided
        self.broker_host = broker_host if broker_host is not None else config.MQTT_BROKER_HOST
        self.broker_port = broker_port if broker_port is not None else config.MQTT_BROKER_PORT
        self.topic = topic if topic is not None else config.MQTT_TOPIC
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """
        Callback for when the client connects to the broker
        """
        logger.debug(f"Connected to MQTT broker with result code: {rc}")
        self.connected = True
        client.subscribe(self.topic)
        logger.debug(f"Subscribed to topic: {self.topic}")

    def _on_message(self, client, userdata, msg):
        """
        Callback for when a message is received from the broker
        """
        try:
            logger.debug(f"Received MQTT message: {msg.payload.decode()}")
            payload = json.loads(msg.payload.decode())
            logger.debug(f"Parsed payload: {payload}")
            
            # Update real-time display queue
            if sensor_data_queue.full():
                sensor_data_queue.get()
            sensor_data_queue.put(payload)
            logger.debug("Added to sensor_data_queue")
            
            # Process data for statistics
            data_processor.process_sensor_data(payload)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.debug(f"Error type: {type(e)}")

    def start(self):
        """
        Connect to the MQTT broker and start the client loop in a separate thread
        
        Returns:
            Thread: The thread running the MQTT client loop
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, config.MQTT_KEEPALIVE)
            
            # Start the loop in a separate thread
            thread = Thread(target=self.client.loop_forever, daemon=True)
            thread.start()
            logger.info("MQTT client started")
            return thread
        except Exception as e:
            logger.error(f"Failed to start MQTT client: {e}")
            return None
    
    def stop(self):
        """
        Disconnect from the MQTT broker
        """
        if self.connected:
            self.client.disconnect()
            logger.info("MQTT client stopped")
            self.connected = False

def get_latest_data():
    """
    Get the latest sensor data from the queue
    
    Returns:
        list: List of the latest sensor data
    """
    data = []
    try:
        # Get all items from the queue without blocking
        while not sensor_data_queue.empty():
            data.append(sensor_data_queue.get_nowait())
    except queue.Empty:
        pass
    
    return data
