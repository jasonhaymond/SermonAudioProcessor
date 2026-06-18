#!/usr/bin/env bash
# Sermon Audio Processor - Linux setup script
# ===========================================
# This script prepares a project-local Python virtual environment and installs
# the Python packages required by the sermon processor.
#
# Requirements before running on Ubuntu/Debian:
#   sudo apt update
#   sudo apt install -y python3 python3-venv python3-pip ffmpeg
#
# Usage:
#   chmod +x setup_linux.sh watch_linux.sh batch_linux.sh
#   ./setup_linux.sh

# Stop immediately if a command fails so setup errors are visible.
set -e

# Move to the directory where this script lives. This lets you run the script
# from any current working directory.
cd "$(dirname "$0")"

# Confirm Python 3 exists.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. On Ubuntu/Debian run: sudo apt install python3 python3-venv python3-pip"
  exit 1
fi

# Confirm FFmpeg exists. The app uses ffmpeg for processing and ffprobe for reports.
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg is required. On Ubuntu/Debian run: sudo apt install ffmpeg"
  exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ffprobe is required and normally comes with FFmpeg. Reinstall FFmpeg if needed."
  exit 1
fi

# Create an isolated virtual environment in this project folder.
python3 -m venv .venv

# Activate the virtual environment for the remaining install commands.
source .venv/bin/activate

# Install Python dependencies.
python -m pip install --upgrade pip
pip install -r requirements.txt

# Verify dependencies and create/check configured folders.
python -m sermon_processor --check

echo "Setup complete. Run ./watch_linux.sh to start watching the inbox folder."
