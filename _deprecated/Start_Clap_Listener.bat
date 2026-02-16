@echo off
title Tokyo - Clap Listener (Active)
cd /d "%~dp0"
call .venv\Scripts\activate
echo Waiting for claps...
python clap_launcher.py
pause
