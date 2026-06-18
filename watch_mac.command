#!/usr/bin/env bash
# Sermon Audio Processor - macOS watcher launcher
# Double-click this file in Finder or run it from Terminal.
# It starts continuous watch mode and processes supported files dropped in inbox/.

cd "$(dirname "$0")"
source .venv/bin/activate
python -m sermon_processor --watch
