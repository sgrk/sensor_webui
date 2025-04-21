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
    
    Query parameters:
    - interval: Time interval for data aggregation ('1min', '10min', '1hour', '1day')
    """
    from flask import request
    
    # Get interval from query parameters, default to 1min
    interval = request.args.get('interval', '1min')
    if interval not in ['1min', '10min', '1hour', '1day']:
        interval = '1min'
    
    # Get temperature data
    temp_timestamps, temp_stats = data_processor.get_statistics('temperature', interval=interval)
    
    # Get CO2 data
    co2_timestamps, co2_stats = data_processor.get_statistics('co2', interval=interval)
    
    return jsonify({
        'temperature': {
            'timestamps': temp_timestamps,
            'stats': temp_stats,
            'interval': interval
        },
        'co2': {
            'timestamps': co2_timestamps,
            'stats': co2_stats,
            'interval': interval
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
