@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
:: Start pythonw (no console) and exit batch immediately
start "" pythonw main.py
exit
