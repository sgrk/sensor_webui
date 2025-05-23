import statistics
from datetime import datetime
import logging
from threading import Lock
import utils
import config

# Configure logging
logger = logging.getLogger(__name__)

# Global data storage
minute_data = []  # Store 1 minute of data
minute_data_lock = Lock()  # Lock for thread-safe operations

def calculate_statistics(data_list, reading_type):
    """
    Calculate statistics for a specific reading type from a list of sensor data
    
    Args:
        data_list (list): List of sensor data dictionaries
        reading_type (str): Type of reading to calculate statistics for (e.g., 'temperature', 'co2')
        
    Returns:
        dict or None: Dictionary containing statistics, or None if no data available
    """
    if not data_list:
        return None
    
    # Extract values for the specified reading type
    values = [reading['value'] for item in data_list for reading in item['readings'] 
             if reading['type'] == reading_type]
    
    if not values:
        return None

    # Parse timestamp from the last data point
    last_time = utils.parse_timestamp(data_list[-1]['timestamp'])
    if not last_time:
        return None

    # Calculate statistics
    return {
        'timestamp': last_time.strftime('%Y-%m-%d %H:%M:00'),
        'average': statistics.mean(values),
        'maximum': max(values),
        'minimum': min(values),
        'first': values[0],
        'last': values[-1],
        'count': len(values),  # Add count of elements used in calculation
        'type': reading_type
    }

def save_statistics(stats):
    """
    Save statistics to a CSV file
    
    Args:
        stats (dict): Dictionary containing statistics
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not stats:
        logger.debug("No stats to save")
        return False
    
    try:
        # Remove type from stats before saving (used for filename)
        reading_type = stats.pop('type')
        filename = f'{reading_type}_stats.csv'
        
        # Define CSV field names
        fieldnames = ['timestamp', 'average', 'maximum', 'minimum', 'first', 'last', 'count']
        
        # Save to CSV
        return utils.save_to_csv(filename, stats, fieldnames)
            
    except Exception as e:
        logger.error(f"Critical error in save_statistics: {e}")
        logger.debug(f"Stats object: {stats}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

def process_sensor_data(payload):
    """
    Process incoming sensor data
    
    Args:
        payload (dict): Sensor data payload
        
    Returns:
        bool: True if data was processed successfully
    """
    try:
        logger.debug(f"Processing sensor data: {payload}")
        
        # Add to minute data for statistics
        with minute_data_lock:
            minute_data.append(payload)
            logger.debug(f"Added to minute_data, current size: {len(minute_data)}")
        
        # Check if we need to calculate statistics
        check_and_save_minute_data()
        
        return True
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        return False

def check_and_save_minute_data():
    """
    Check if we need to calculate and save statistics for the current minute data
    
    Returns:
        bool: True if statistics were calculated and saved
    """
    global minute_data
    current_time = datetime.now()
    
    if not minute_data:
        return False
    
    logger.debug(f"First data in minute_data: {minute_data[0]}")
        
    # Parse timestamp from first data point
    first_time = utils.parse_timestamp(minute_data[0]['timestamp'])
    if not first_time:
        logger.debug(f"Failed to parse timestamp: {minute_data[0]['timestamp']}")
        return False
    
    logger.debug(f"Parsed timestamp: {first_time}")
    logger.debug(f"Current time: {current_time}")
    
    # If the minute has changed, process the previous minute's data
    if first_time.minute != current_time.minute:
        logger.debug(f"Processing data for minute: {first_time.minute}")
        with minute_data_lock:
            # Calculate and save temperature statistics
            temp_stats = calculate_statistics(minute_data, 'temperature')
            if temp_stats:
                logger.debug(f"Temperature stats: {temp_stats}")
                save_statistics(temp_stats)
            else:
                logger.debug("Failed to calculate temperature stats")
            
            # Calculate and save CO2 statistics
            co2_stats = calculate_statistics(minute_data, 'co2')
            if co2_stats:
                logger.debug(f"CO2 stats: {co2_stats}")
                save_statistics(co2_stats)
            else:
                logger.debug("Failed to calculate CO2 stats")
            
            minute_data = []  # Reset data
            return True
    
    return False

def get_statistics(reading_type, limit=None):
    """
    Get statistics for a specific reading type
    
    Args:
        reading_type (str): Type of reading to get statistics for (e.g., 'temperature', 'co2')
        limit (int): Maximum number of records to return
        
    Returns:
        tuple: (timestamps, stats) where timestamps is a list of formatted timestamps
               and stats is a list of dictionaries containing the statistics
    """
    # Use config value if limit is not specified
    if limit is None:
        limit = config.STATS_LIMIT
    filename = f'{reading_type}_stats.csv'
    return utils.read_csv_data(filename, limit)
