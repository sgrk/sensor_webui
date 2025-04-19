# Sensor WebUI

A web application for visualizing temperature and CO2 sensor data. Receives data via MQTT, displays it in real-time, and stores statistical information every minute.

## Features

- MQTT sensor data reception
- Real-time temperature and CO2 level monitoring
- Per-minute statistical data calculation and storage
  - Average value
  - Maximum value
  - Minimum value
  - First value
  - Last value
- Statistical data visualization using candlestick charts
  - Blue: Rising period
  - Red: Falling period
  - Box: First value to last value
  - Whiskers: Minimum to maximum value

## Setup

1. Prerequisites
   - Python 3.8 or higher
   - MQTT Broker (e.g., Mosquitto)

2. Installation
   ```bash
   # Clone the repository
   git clone https://github.com/sgrk/sensor_webui.git
   cd sensor_webui

   # Run setup script
   ./setup.sh
   ```

3. Running the Application
   ```bash
   # Activate virtual environment (if not already activated)
   source venv/bin/activate

   # Start the application
   python app.py
   ```

4. Access http://localhost:5000 in your browser

## MQTT Message Format

```json
{
  "sensor_id": "livingroom_env_01",
  "timestamp": "2025-04-17T20:45:00+09:00",
  "readings": [
    {
      "type": "temperature",
      "value": 23.5,
      "unit": "°C"
    },
    {
      "type": "co2",
      "value": 620,
      "unit": "ppm"
    }
  ]
}
```

## Data Storage

Statistical data is stored in the following CSV files:
- `temperature_stats.csv`: Temperature statistics
- `co2_stats.csv`: CO2 level statistics

Each file contains the following columns:
- timestamp: Data timestamp (end of one-minute period)
- average: One-minute average value
- maximum: One-minute maximum value
- minimum: One-minute minimum value
- first: First value in the one-minute period
- last: Last value in the one-minute period
