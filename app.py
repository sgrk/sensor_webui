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

def calculate_statistics(data_list, reading_type):
    if not data_list:
        return None
    
    values = [reading['value'] for item in data_list for reading in item['readings'] 
             if reading['type'] == reading_type]
    
    if not values:
        return None

    return {
        'timestamp': datetime.fromtimestamp(data_list[-1]['timestamp']).strftime('%Y-%m-%d %H:%M:00'),
        'average': statistics.mean(values),
        'maximum': max(values),
        'minimum': min(values),
        'first': values[0],
        'last': values[-1],
        'type': reading_type
    }

def save_statistics(stats):
    if not stats:
        return
    
    reading_type = stats.pop('type')  # Remove type from stats before saving
    filename = f'{reading_type}_stats.csv'
    file_exists = os.path.exists(filename)
    
    with open(filename, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['timestamp', 'average', 'maximum', 'minimum', 'first', 'last'])
        if not file_exists:
            writer.writeheader()
        writer.writerow(stats)

def check_and_save_minute_data():
    global minute_data
    current_time = datetime.now()
    
    # 現在の分が変わった場合、前の分のデータを処理
    if minute_data and datetime.fromtimestamp(minute_data[0]['timestamp']).minute != current_time.minute:
        with minute_data_lock:
            # 温度の統計を計算・保存
            temp_stats = calculate_statistics(minute_data, 'temperature')
            if temp_stats:
                save_statistics(temp_stats)
            
            # CO2の統計を計算・保存
            co2_stats = calculate_statistics(minute_data, 'co2')
            if co2_stats:
                save_statistics(co2_stats)
            
            minute_data = []  # データをリセット

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sensor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        .chart-container {
            width: 800px;
            margin: 20px auto;
        }
    </style>
</head>
<body>
    <div class="chart-container">
        <h2>Temperature Statistics (°C)</h2>
        <canvas id="tempChart" width="800" height="400"></canvas>
    </div>
    <div class="chart-container">
        <h2>CO2 Statistics (ppm)</h2>
        <canvas id="co2Chart" width="800" height="400"></canvas>
    </div>
    <script>
        // カスタムチャートタイプの定義
        Chart.defaults.candlestick = Chart.defaults.bar;
        Chart.controllers.candlestick = Chart.controllers.bar.extend({
            draw: function() {
                var ctx = this.chart.ctx;
                var elements = this.getMeta().data;
                elements.forEach(function(element) {
                    var data = element._model;
                    var stats = element._stats;
                    
                    // 上昇/下落の色を設定
                    var color = stats.first <= stats.last ? 'blue' : 'red';
                    
                    // ひげ（最大値・最小値）を描画
                    ctx.beginPath();
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1;
                    ctx.moveTo(data.x, data.y);
                    ctx.lineTo(data.x, stats.minY);
                    ctx.moveTo(data.x, data.base);
                    ctx.lineTo(data.x, stats.maxY);
                    ctx.stroke();
                    
                    // 箱（first-last）を描画
                    var boxWidth = element._view.width;
                    var boxY = Math.min(stats.firstY, stats.lastY);
                    var boxHeight = Math.abs(stats.firstY - stats.lastY);
                    
                    ctx.fillStyle = color;
                    ctx.fillRect(data.x - boxWidth/2, boxY, boxWidth, boxHeight || 1);
                });
            }
        });

        function createCandlestickChart(ctx, label, unit) {
            return new Chart(ctx, {
                type: 'candlestick',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        backgroundColor: 'rgba(0,0,0,0)'
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: { 
                            display: true,
                            title: { display: true, text: 'Time' }
                        },
                        y: { 
                            display: true,
                            title: { display: true, text: unit }
                        }
                    },
                    parsing: false,
                    animation: false
                }
            });
        }

        const tempCtx = document.getElementById('tempChart').getContext('2d');
        const co2Ctx = document.getElementById('co2Chart').getContext('2d');
        
        const tempChart = createCandlestickChart(tempCtx, 'Temperature', '°C');
        const co2Chart = createCandlestickChart(co2Ctx, 'CO2', 'ppm');

        function processStats(stats, scale) {
            if (!stats || !stats.length) return [];
            
            return stats.map(stat => {
                const scaleY = scale.getPixelForValue.bind(scale);
                return {
                    _stats: {
                        first: stat.first,
                        last: stat.last,
                        min: stat.minimum,
                        max: stat.maximum,
                        firstY: scaleY(stat.first),
                        lastY: scaleY(stat.last),
                        minY: scaleY(stat.minimum),
                        maxY: scaleY(stat.maximum)
                    },
                    y: Math.min(stat.first, stat.last),
                    base: Math.max(stat.first, stat.last)
                };
            });
        }

        async function fetchData() {
            const res = await fetch('/stats');
            const json = await res.json();
            
            tempChart.data.labels = json.temperature.timestamps;
            tempChart.data.datasets[0].data = processStats(json.temperature.stats, tempChart.scales.y);
            tempChart.update();
            
            co2Chart.data.labels = json.co2.timestamps;
            co2Chart.data.datasets[0].data = processStats(json.co2.stats, co2Chart.scales.y);
            co2Chart.update();
        }

        setInterval(fetchData, 10000);  // 10秒ごとに更新
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

def read_stats_file(filename, limit=60):
    """
    CSVファイルから統計データを読み込む
    limit: 返す最大レコード数（デフォルト1時間分）
    """
    if not os.path.exists(filename):
        return [], []
        
    timestamps = []
    stats = []
    
    with open(filename, 'r', newline='') as f:
        reader = csv.DictReader(f)
        rows = list(reader)[-limit:]  # 最新のN件を取得
        
        for row in rows:
            timestamps.append(row['timestamp'])
            stats.append({
                'minimum': float(row['minimum']),
                'maximum': float(row['maximum']),
                'first': float(row['first']),
                'last': float(row['last']),
                'average': float(row['average'])
            })
    
    return timestamps, stats

@app.route('/stats')
def get_stats():
    # 温度データの読み込み
    temp_timestamps, temp_stats = read_stats_file('temperature_stats.csv')
    
    # CO2データの読み込み
    co2_timestamps, co2_stats = read_stats_file('co2_stats.csv')
    
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
