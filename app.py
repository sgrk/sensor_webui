from flask import Flask, render_template, jsonify
import logging
from threading import Thread
import mqtt_client
import data_processor
import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

@app.route('/')
def index():
    """
    Render the main dashboard page
    """
    return render_template('index.html')

@app.route('/stats')
def get_stats():
    """
    API endpoint to get sensor statistics
    """
    # Get temperature data
    temp_timestamps, temp_stats = data_processor.get_statistics('temperature')
    
    # Get CO2 data
    co2_timestamps, co2_stats = data_processor.get_statistics('co2')
    
    return jsonify({
        'temperature': {
            'timestamps': temp_timestamps,
            'stats': temp_stats
        },
        'co2': {
            'timestamps': co2_timestamps,
            'stats': co2_stats
        }
    })

@app.route('/latest')
def get_latest():
    """
    API endpoint to get the latest sensor data
    """
    return jsonify(mqtt_client.get_latest_data())

def start_mqtt_client():
    """
    Start the MQTT client
    """
    client = mqtt_client.MQTTClient()
    return client.start()

# Main entry point
if __name__ == "__main__":
    # Start MQTT client in a separate thread
    mqtt_thread = start_mqtt_client()
    
# Start Flask app
    logger.info(f"Starting Flask application on {config.FLASK_HOST}:{config.FLASK_PORT}")
    app.run(host=config.FLASK_HOST, port=config.FLASK_PORT, debug=config.FLASK_DEBUG)
