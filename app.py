from flask import Flask, render_template_string, jsonify
from threading import Thread, Lock
import time
import json
import queue
import paho.mqtt.client as mqtt
from datetime import datetime
import csv
import os
import statistics

app = Flask(__name__)
sensor_data_queue = queue.Queue(maxsize=100)
minute_data = []  # 1分間のデータを保持
minute_data_lock = Lock()  # スレッドセーフな操作のためのロック

def calculate_statistics(data_list):
    if not data_list:
        return None
    
    values = [reading['value'] for item in data_list for reading in item['readings'] 
             if reading['type'] == 'temperature']
    
    if not values:
        return None

    return {
        'timestamp': datetime.fromtimestamp(data_list[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:00'),
        'average': statistics.mean(values),
        'maximum': max(values),
        'minimum': min(values),
        'first': values[0],
        'last': values[-1]
    }

def save_statistics(stats):
    if not stats:
        return
    
    filename = 'temperature_stats.csv'
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'average', 'maximum', 'minimum', 'first', 'last'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(stats)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sensor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h2>Live Temperature Data</h2>
    <canvas id="tempChart" width="800" height="400"></canvas>
    <script>
        const ctx = document.getElementById('tempChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature (°C)',
                    data: [],
                    borderColor: 'blue',
                    fill: false
                }]
            },
            options: {
                scales: {
                    x: { display: true, title: { display: true, text: 'Timestamp' }},
                    y: { display: true, title: { display: true, text: '°C' }}
                }
            }
        });

        async function fetchData() {
            const res = await fetch('/data');
            const json = await res.json();
            chart.data.labels = json.timestamps;
            chart.data.datasets[0].data = json.temperatures;
            chart.update();
        }

        setInterval(fetchData, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    temperatures = []
    timestamps = []
    for item in list(sensor_data_queue.queue):
        for reading in item['readings']:
            if reading['type'] == 'temperature':
                temperatures.append(reading['value'])
                timestamps.append(item['timestamp'])
    return jsonify({'temperatures': temperatures, 'timestamps': timestamps})

def check_and_save_minute_data():
    global minute_data
    current_time = datetime.now()
    
    # 現在の分が変わった場合、前の分のデータを処理
    if minute_data and datetime.fromtimestamp(minute_data[0]['timestamp']).minute != current_time.minute:
        with minute_data_lock:
            stats = calculate_statistics(minute_data)
            if stats:
                save_statistics(stats)
            minute_data = []  # データをリセット

def mqtt_listener():
    def on_connect(client, userdata, flags, rc):
        client.subscribe("home/livingroom/env/sensor1")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            
            # リアルタイム表示用のキュー更新
            if sensor_data_queue.full():
                sensor_data_queue.get()
            sensor_data_queue.put(payload)
            
            # 1分間の統計データ用の処理
            with minute_data_lock:
                minute_data.append(payload)
            
            # 毎分の統計処理
            check_and_save_minute_data()
            
        except Exception as e:
            print("Error:", e)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("127.0.0.1", 1883, 60)
    client.loop_forever()

# MQTTを別スレッドで開始
Thread(target=mqtt_listener, daemon=True).start()

# Flask起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
