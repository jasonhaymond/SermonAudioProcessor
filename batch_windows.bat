@echo off
REM Sermon Audio Processor - Windows batch launcher
REM Double-click this file to process supported files already in inbox\ one time.

cd /d "%~dp0"
.venv\Scripts\python.exe -m sermon_processor --batch
pause
