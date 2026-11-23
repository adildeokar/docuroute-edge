@echo off
REM One-time setup: installs the Python libraries
cd /d "%~dp0"
python -m pip install -r requirements.txt
echo.
echo Setup complete. Now run: run.bat
pause
