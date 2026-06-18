@echo off
REM Sermon Audio Processor - Windows watcher launcher
REM Double-click this file to start continuous watch mode.
REM Files dropped into inbox\ are processed into output\ as MP3.

cd /d "%~dp0"
.venv\Scripts\python.exe -m sermon_processor --watch
pause
