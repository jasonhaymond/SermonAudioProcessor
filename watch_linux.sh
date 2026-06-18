#!/usr/bin/env bash
# Sermon Audio Processor - Linux watcher launcher
# Starts continuous watch mode. Files dropped into inbox/ are processed into output/ as MP3.

set -e
cd "$(dirname "$0")"
source .venv/bin/activate
python -m sermon_processor --watch
