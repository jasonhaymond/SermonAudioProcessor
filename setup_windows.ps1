# Sermon Audio Processor - Windows setup script
# =============================================
# This PowerShell script prepares a local Python virtual environment and installs
# the Python packages required by the sermon processor.
#
# Requirements before running:
#   1. Python 3.10+ installed and available as python
#   2. FFmpeg installed and available in PATH as ffmpeg/ffprobe
#
# Recommended installs from PowerShell:
#   winget install Python.Python.3.12
#   winget install Gyan.FFmpeg
#
# If PowerShell blocks the script, run this first in the same PowerShell window:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Move into the folder containing this script.
Set-Location $PSScriptRoot

# Check Python.
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Error "Python is required. Install Python 3 from python.org, winget, or Microsoft Store."
  exit 1
}

# Check FFmpeg and ffprobe. Both are required.
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
  Write-Error "FFmpeg is required and must be available in PATH. Install with: winget install Gyan.FFmpeg"
  exit 1
}

if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
  Write-Error "ffprobe is required and normally comes with FFmpeg. Reinstall FFmpeg if needed."
  exit 1
}

# Create a project-local virtual environment so dependencies stay isolated.
python -m venv .venv

# Upgrade pip and install required Python packages.
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\pip.exe install -r requirements.txt

# Ask the app to verify FFmpeg and create/check all configured folders.
.\.venv\Scripts\python.exe -m sermon_processor --check

Write-Host "Setup complete. Run watch_windows.bat to start watching the inbox folder."
