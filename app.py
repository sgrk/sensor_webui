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

    # 最後のデータのタイムスタンプを解析
    last_time = parse_timestamp(data_list[-1]['timestamp'])
    if not last_time:
        return None

    return {
        'timestamp': last_time.strftime('%Y-%m-%d %H:%M:00'),
        'average': statistics.mean(values),
        'maximum': max(values),
        'minimum': min(values),
        'first': values[0],
        'last': values[-1],
        'type': reading_type
    }

def save_statistics(stats):
    if not stats:
        print("Debug - No stats to save")
        return
    
    try:
        reading_type = stats.pop('type')  # Remove type from stats before saving
        filename = f'{reading_type}_stats.csv'
        file_exists = os.path.exists(filename)
        
        print(f"Debug - Saving stats to {filename}:")
        print(stats)
        
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'average', 'maximum', 'minimum', 'first', 'last'])
            if not file_exists:
                writer.writeheader()
                print(f"Debug - Created new file with headers: {filename}")
            writer.writerow(stats)
            print(f"Debug - Successfully wrote stats to {filename}")
            
    except Exception as e:
        print(f"Error saving statistics: {e}")
        print(f"Debug - Stats object: {stats}")

def parse_timestamp(timestamp_str):
    """ISO形式のタイムスタンプ文字列をdatetimeオブジェクトに変換"""
    try:
        # タイムゾーン情報を含むISO形式のタイムスタンプを解析
        dt = datetime.fromisoformat(timestamp_str)
        # タイムゾーン情報を除去（ローカル時間として扱う）
        return dt.replace(tzinfo=None)
    except ValueError as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return None

def check_and_save_minute_data():
    global minute_data
    current_time = datetime.now()
    
    if not minute_data:
        return
    
    print("Debug - First data in minute_data:", minute_data[0])
        
    # 最初のデータのタイムスタンプを解析
    first_time = parse_timestamp(minute_data[0]['timestamp'])
    if not first_time:
        print("Debug - Failed to parse timestamp:", minute_data[0]['timestamp'])
        return
    
    print("Debug - Parsed timestamp:", first_time)
    print("Debug - Current time:", current_time)
    
    # 現在の分が変わった場合、前の分のデータを処理
    if first_time.minute != current_time.minute:
        print("Debug - Processing data for minute:", first_time.minute)
        with minute_data_lock:
            # 温度の統計を計算・保存
            temp_stats = calculate_statistics(minute_data, 'temperature')
            if temp_stats:
                print("Debug - Temperature stats:", temp_stats)
                save_statistics(temp_stats)
            else:
                print("Debug - Failed to calculate temperature stats")
            
            # CO2の統計を計算・保存
            co2_stats = calculate_statistics(minute_data, 'co2')
            if co2_stats:
                print("Debug - CO2 stats:", co2_stats)
                save_statistics(co2_stats)
            else:
                print("Debug - Failed to calculate CO2 stats")
            
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
        function createStatChart(ctx, label, unit) {
            return new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: [],
                    datasets: [{
                        label: label,
                        data: [],
                        borderWidth: 1,
                        borderColor: 'rgba(0,0,0,0)',
                        backgroundColor: 'rgba(0,0,0,0)'
                    }]
                },
                options: {
                    responsive: true,
                    animation: false,
                    scales: {
                        x: { 
                            display: true,
                            title: { display: true, text: 'Time' },
                            grid: {
                                display: true,
                                color: 'rgba(0,0,0,0.1)'
                            }
                        },
                        y: { 
                            display: true,
                            title: { display: true, text: unit },
                            grid: {
                                display: true,
                                color: 'rgba(0,0,0,0.1)'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        },
                        tooltip: {
                            enabled: true,
                            callbacks: {
                                label: function(context) {
                                    const stat = context.raw;
                                    return [
                                        `First: ${stat.first} ${unit}`,
                                        `Last: ${stat.last} ${unit}`,
                                        `Min: ${stat.minimum} ${unit}`,
                                        `Max: ${stat.maximum} ${unit}`,
                                        `Avg: ${stat.y} ${unit}`
                                    ];
                                }
                            }
                        }
                    }
                }
            });
        }

        const tempCtx = document.getElementById('tempChart').getContext('2d');
        const co2Ctx = document.getElementById('co2Chart').getContext('2d');
        
        const tempChart = createStatChart(tempCtx, 'Temperature', '°C');
        const co2Chart = createStatChart(co2Ctx, 'CO2', 'ppm');

        function createCandlestickDataset(data) {
            if (!data || !data.stats) return null;
            
            return {
                label: 'Statistics',
                data: data.stats.map(stat => ({
                    x: null,  // Will be set by Chart.js
                    o: stat.first,    // open
                    h: stat.maximum,   // high
                    l: stat.minimum,   // low
                    c: stat.last,      // close
                })),
                color: {
                    up: 'blue',
                    down: 'red',
                },
                borderWidth: 2,
                type: 'candlestick'
            };
        }

        function updateChart(chart, data) {
            if (!data || !data.timestamps || !data.stats || data.timestamps.length === 0) {
                console.log("No data to display");
                return;
            }

            console.log("Updating chart with data:", data);

            // Y軸の範囲を計算
            const allValues = data.stats.reduce((acc, stat) => {
                acc.push(stat.minimum, stat.maximum, stat.first, stat.last);
                return acc;
            }, []);
            const minValue = Math.min(...allValues);
            const maxValue = Math.max(...allValues);
            const padding = (maxValue - minValue) * 0.1;

            // チャートの更新
            chart.data.labels = data.timestamps;
            chart.data.datasets = [{
                label: chart.canvas.id === 'tempChart' ? 'Temperature' : 'CO2',
                data: data.stats.map((stat, i) => ({
                    x: i,
                    y: stat.average,
                    minimum: stat.minimum,
                    maximum: stat.maximum,
                    first: stat.first,
                    last: stat.last
                })),
                borderColor: 'rgba(0,0,0,0)',
                backgroundColor: 'rgba(0,0,0,0)'
            }];

            chart.options.scales.y.min = minValue - padding;
            chart.options.scales.y.max = maxValue + padding;

            // アニメーションなしで更新
            chart.update('none');

            // カスタム描画
            const ctx = chart.ctx;
            const yScale = chart.scales.y;
            const xScale = chart.scales.x;

            data.stats.forEach((stat, i) => {
                const x = xScale.getPixelForValue(i);
                const width = xScale.getPixelForValue(1) - xScale.getPixelForValue(0);
                const candleWidth = Math.min(width * 0.8, 15);  // キャンドルの幅を制限

                // 上昇/下落の色を決定
                const color = stat.first <= stat.last ? 'blue' : 'red';

                // ひげを描画（最小値から最大値）
                ctx.beginPath();
                ctx.strokeStyle = color;
                ctx.lineWidth = 1;
                ctx.moveTo(x, yScale.getPixelForValue(stat.minimum));
                ctx.lineTo(x, yScale.getPixelForValue(stat.maximum));
                ctx.stroke();

                // 箱を描画（始値から終値）
                const firstY = yScale.getPixelForValue(stat.first);
                const lastY = yScale.getPixelForValue(stat.last);
                const boxTop = Math.min(firstY, lastY);
                const boxHeight = Math.abs(firstY - lastY) || 1;

                ctx.fillStyle = color;
                ctx.fillRect(x - candleWidth/2, boxTop, candleWidth, boxHeight);
            });
        }
        }

        async function fetchData() {
            try {
                const res = await fetch('/stats');
                const json = await res.json();
                
                updateChart(tempChart, json.temperature);
                updateChart(co2Chart, json.co2);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        // 初回データ取得
        fetchData();
        // 10秒ごとに更新
        setInterval(fetchData, 10000);
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
        print(f"Debug - File does not exist: {filename}")
        return [], []
        
    timestamps = []
    stats = []
    
    try:
        with open(filename, 'r', newline='') as f:
            # ファイルの内容を確認
            content = f.read()
            print(f"Debug - File content of {filename}:")
            print(content)
            
            # ファイルポインタを先頭に戻す
            f.seek(0)
            
            # ヘッダーを確認
            first_line = f.readline().strip()
            print(f"Debug - First line (header): {first_line}")
            
            # ファイルポインタを先頭に戻す
            f.seek(0)
            
            reader = csv.DictReader(f)
            print(f"Debug - CSV headers: {reader.fieldnames}")
            
            # 全ての行を読み込む
            all_rows = list(reader)
            print(f"Debug - Total rows read: {len(all_rows)}")
            
            # 最新のN件を取得
            rows = all_rows[-limit:] if len(all_rows) > limit else all_rows
            
            for row in rows:
                try:
                    # タイムスタンプを時:分の形式に変換
                    dt = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:00')
                    timestamps.append(dt.strftime('%H:%M'))
                    
                    stats.append({
                        'minimum': float(row['minimum']),
                        'maximum': float(row['maximum']),
                        'first': float(row['first']),
                        'last': float(row['last']),
                        'average': float(row['average'])
                    })
                except Exception as e:
                    print(f"Debug - Error processing row: {row}")
                    print(f"Debug - Error details: {e}")
                    continue
                
    except Exception as e:
        print(f"Error reading stats file {filename}: {e}")
        return [], []
    
    print(f"Debug - Successfully processed {len(stats)} records from {filename}")
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

# この関数は削除（上部に正しいバージョンが既にある）

def mqtt_listener():
    def on_connect(client, userdata, flags, rc):
        print("Debug - Connected to MQTT broker with result code:", rc)
        client.subscribe("home/livingroom/env/sensor1")
        print("Debug - Subscribed to topic: home/livingroom/env/sensor1")

    def on_message(client, userdata, msg):
        try:
            print("\nDebug - Received MQTT message:", msg.payload.decode())
            payload = json.loads(msg.payload.decode())
            print("Debug - Parsed payload:", payload)
            
            # リアルタイム表示用のキュー更新
            if sensor_data_queue.full():
                sensor_data_queue.get()
            sensor_data_queue.put(payload)
            print("Debug - Added to sensor_data_queue")
            
            # 1分間の統計データ用の処理
            with minute_data_lock:
                minute_data.append(payload)
                print("Debug - Added to minute_data, current size:", len(minute_data))
            
            # 毎分の統計処理
            check_and_save_minute_data()
            
        except json.JSONDecodeError as e:
            print("Debug - JSON decode error:", e)
        except Exception as e:
            print("Debug - Unexpected error:", e)
            print("Debug - Error type:", type(e))

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
