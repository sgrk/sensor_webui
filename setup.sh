#!/bin/bash

# エラーが発生したら停止
set -e

# スクリプトのディレクトリに移動
cd "$(dirname "$0")"

# Python 3がインストールされているか確認
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# venvがインストールされているか確認
python3 -c "import venv" &> /dev/null || {
    echo "Python venv module is not installed. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y python3-venv
    elif command -v yum &> /dev/null; then
        sudo yum install -y python3-venv
    else
        echo "Could not install python3-venv. Please install it manually."
        exit 1
    fi
}

# 既存のvenv環境を削除（存在する場合）
if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

# 新しいvenv環境を作成
echo "Creating new virtual environment..."
python3 -m venv venv

# venv環境をアクティベート
echo "Activating virtual environment..."
source venv/bin/activate

# 依存関係をインストール
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# config.pyが存在しない場合、config.py.sampleをコピー
if [ ! -f "config.py" ]; then
    echo "config.py not found. Creating from config.py.sample..."
    cp config.py.sample config.py
    echo "Created config.py from sample file."
fi

echo "Setup completed successfully!"
echo "To activate the virtual environment, run: source venv/bin/activate"
