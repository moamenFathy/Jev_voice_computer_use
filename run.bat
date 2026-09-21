@echo off
chcp 65001 > nul
title المساعد الصوتي للتحكم بالكمبيوتر - Arabic Computer Use
echo ========================================================
echo   🤖 جاري تشغيل المساعد الصوتي للتحكم بالكمبيوتر...
echo ========================================================

cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [*] إعداد البيئة...
    uv venv --python 3.11 --allow-existing venv
    uv pip install -r requirements.txt --python .\venv\Scripts\python.exe
    uv pip install pyaudio --python .\venv\Scripts\python.exe
)

echo [*] تشغيل البرنامج...
.\venv\Scripts\python.exe main.py

pause
