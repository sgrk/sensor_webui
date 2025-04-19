from datetime import datetime
import os
import csv
import logging
import config

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_timestamp(timestamp_str):
    """
    Convert ISO format timestamp string to datetime object
    
    Args:
        timestamp_str (str): ISO format timestamp string
        
    Returns:
        datetime or None: Parsed datetime object without timezone info, or None if parsing fails
    """
    try:
        # Parse ISO format timestamp with timezone info
        dt = datetime.fromisoformat(timestamp_str)
        # Remove timezone info (treat as local time)
        return dt.replace(tzinfo=None)
    except ValueError as e:
        logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
        return None

def ensure_data_directory():
    """
    Ensure the data directory exists
    
    Returns:
        str: Absolute path to the data directory
    """
    data_dir = os.path.abspath(config.DATA_DIRECTORY)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.debug(f"Created directory: {data_dir}")
    return data_dir

def save_to_csv(filename, data, fieldnames):
    """
    Save data to a CSV file
    
    Args:
        filename (str): Name of the CSV file (without path)
        data (dict): Dictionary containing data to save
        fieldnames (list): List of field names for CSV header
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        data_dir = ensure_data_directory()
        filepath = os.path.join(data_dir, filename)
        file_exists = os.path.exists(filepath)
        
        logger.debug(f"Saving data to {filepath}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Open file in append mode
        with open(filepath, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                logger.debug(f"Created new file with headers: {filepath}")
            writer.writerow(data)
            logger.debug(f"Successfully wrote data to {filepath}")
        
        return True
    except Exception as e:
        logger.error(f"Error saving to CSV {filename}: {e}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return False

def read_csv_data(filename, limit=None):
    # Use config value if limit is not specified
    if limit is None:
        limit = config.STATS_LIMIT
    """
    Read data from a CSV file
    
    Args:
        filename (str): Name of the CSV file (without path)
        limit (int): Maximum number of records to return
        
    Returns:
        tuple: (timestamps, data) where timestamps is a list of formatted timestamps
               and data is a list of dictionaries containing the data
    """
    data_dir = ensure_data_directory()
    filepath = os.path.join(data_dir, filename)
    
    if not os.path.exists(filepath):
        logger.debug(f"File does not exist: {filepath}")
        return [], []
    
    logger.debug(f"Reading from file: {filepath}")
    
    timestamps = []
    data_list = []
    
    try:
        with open(filepath, 'r', newline='') as f:
            reader = csv.DictReader(f)
            
            # Read all rows
            all_rows = list(reader)
            logger.debug(f"Total rows read: {len(all_rows)}")
            
            # Get the latest N records
            rows = all_rows[-limit:] if len(all_rows) > limit else all_rows
            
            for row in rows:
                try:
                    # Convert timestamp to HH:MM format
                    dt = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:00')
                    timestamps.append(dt.strftime('%H:%M'))
                    
                    # Convert string values to float
                    data_list.append({
                        'minimum': float(row['minimum']),
                        'maximum': float(row['maximum']),
                        'first': float(row['first']),
                        'last': float(row['last']),
                        'average': float(row['average'])
                    })
                except Exception as e:
                    logger.debug(f"Error processing row: {row}")
                    logger.debug(f"Error details: {e}")
                    continue
    except Exception as e:
        logger.error(f"Error reading CSV file {filename}: {e}")
        return [], []
    
    logger.debug(f"Successfully processed {len(data_list)} records from {filename}")
    return timestamps, data_list
