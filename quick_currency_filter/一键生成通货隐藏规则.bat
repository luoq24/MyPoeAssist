@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"
"D:\Pycharm_Files\.venv\Scripts\python.exe" main.py
pause
