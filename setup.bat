@echo off
setlocal enabledelayedexpansion

:: エラーが発生したら停止
:: (Windows batch doesn't have a direct equivalent to set -e, but we'll use error checking)

:: スクリプトのディレクトリに移動
cd /d "%~dp0"

:: Python 3がインストールされているか確認
python --version 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Please install Python first.
    exit /b 1
)

:: venvがインストールされているか確認
python -c "import venv" 2>nul
if %ERRORLEVEL% neq 0 (
    echo Python venv module is not installed. Please install it manually.
    exit /b 1
)

:: 既存のvenv環境を削除（存在する場合）
if exist venv (
    echo Removing existing virtual environment...
    rmdir /s /q venv
)

:: 新しいvenv環境を作成
echo Creating new virtual environment...
python -m venv venv

:: venv環境をアクティベート
echo Activating virtual environment...
call venv\Scripts\activate.bat

:: 依存関係をインストール
echo Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

:: config.pyが存在しない場合、config.py.sampleをコピー
if not exist config.py (
    echo config.py not found. Creating from config.py.sample...
    copy config.py.sample config.py
    echo Created config.py from sample file.
)

echo Setup completed successfully!
echo To activate the virtual environment, run: venv\Scripts\activate.bat

endlocal
