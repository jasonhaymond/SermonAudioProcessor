#!/usr/bin/env bash
# Sermon Audio Processor - macOS setup script
# ===========================================
# This script prepares a local Python virtual environment and installs the
# Python packages required by the sermon processor.
#
# Requirements before running:
#   1. Python 3.10+ installed and available as python3
#   2. FFmpeg installed and available as ffmpeg/ffprobe
#
# Recommended FFmpeg install on macOS:
#   brew install ffmpeg
#
# Usage:
#   chmod +x setup_mac.sh watch_mac.command batch_mac.command
#   ./setup_mac.sh

# Exit immediately if any command fails. This prevents a half-installed setup
# from looking successful.
set -e

# Move into the project folder no matter where the script was launched from.
cd "$(dirname "$0")"

# Check Python. macOS usually includes a python3 command if Python is installed.
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required. Install it from https://www.python.org/ or with Homebrew."
  exit 1
fi

# Check FFmpeg. The processor uses both ffmpeg and ffprobe.
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "FFmpeg is not installed. If you use Homebrew, run: brew install ffmpeg"
  exit 1
fi

if ! command -v ffprobe >/dev/null 2>&1; then
  echo "ffprobe is not installed. It normally comes with FFmpeg. Reinstall FFmpeg if needed."
  exit 1
fi

# Create an isolated Python environment inside this folder. This avoids changing
# global Python packages on your Mac.
python3 -m venv .venv

# Activate the virtual environment for this setup session.
source .venv/bin/activate

# Install/upgrade pip and then install required packages from requirements.txt.
python -m pip install --upgrade pip
pip install -r requirements.txt

# Ask the app to verify FFmpeg and create/check all configured folders.
python -m sermon_processor --check

echo "Setup complete. Run ./watch_mac.command to start watching the inbox folder."
