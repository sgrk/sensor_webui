# Sensor WebUI

A web application for visualizing temperature and CO2 sensor data. Receives data via MQTT, displays it in real-time, and stores statistical information every minute.

# センサーWebUI

MQTTを介して温度とCO2センサーデータを受信し、リアルタイムで表示し、毎分統計情報を保存するWebアプリケーションです。

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

## 機能

- MQTTセンサーデータの受信
- 温度とCO2レベルのリアルタイムモニタリング
- 毎分の統計データ計算と保存
  - 平均値
  - 最大値
  - 最小値
  - 最初の値
  - 最後の値
- ローソク足チャートを使用した統計データの可視化
  - 青: 上昇期間
  - 赤: 下降期間
  - ボックス: 最初の値から最後の値まで
  - ひげ: 最小値から最大値まで

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

## セットアップ

1. 前提条件
   - Python 3.8以上
   - MQTTブローカー（例：Mosquitto）

2. インストール
   ```bash
   # リポジトリをクローン
   git clone https://github.com/sgrk/sensor_webui.git
   cd sensor_webui

   # セットアップスクリプトを実行
   ./setup.sh
   ```

3. アプリケーションの実行
   ```bash
   # 仮想環境を有効化（まだ有効化されていない場合）
   source venv/bin/activate

   # アプリケーションを起動
   python app.py
   ```

4. ブラウザでhttp://localhost:5000にアクセス

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

## MQTTメッセージフォーマット

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

## データストレージ

統計データは以下のCSVファイルに保存されます：
- `temperature_stats.csv`：温度統計
- `co2_stats.csv`：CO2レベル統計

各ファイルには以下の列が含まれます：
- timestamp：データのタイムスタンプ（1分間の期間の終了時）
- average：1分間の平均値
- maximum：1分間の最大値
- minimum：1分間の最小値
- first：1分間の期間の最初の値
- last：1分間の期間の最後の値

## システム構成

このアプリケーションは以下のコンポーネントで構成されています：
- `app.py`：Flaskウェブアプリケーションのメインエントリーポイント
- `mqtt_client.py`：MQTTブローカーからデータを受信するクライアント
- `data_processor.py`：センサーデータの処理と統計計算
- `utils.py`：ユーティリティ関数
- `config.py`：アプリケーション設定

## 技術スタック

- バックエンド：Python、Flask
- フロントエンド：HTML、CSS、JavaScript、Chart.js
- データ通信：MQTT
- データストレージ：CSV
