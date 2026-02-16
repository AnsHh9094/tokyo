@echo off
cd /d "%~dp0"
echo Starting Jarvis...
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "main.py"
) else (
    echo Virtual environment not found. Attempting to run with system python...
    start "" pythonw "main.py" 
)
exit
