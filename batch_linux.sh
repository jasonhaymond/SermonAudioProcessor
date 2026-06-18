#!/usr/bin/env bash
# Sermon Audio Processor - Linux batch launcher
# Processes supported files already in inbox/ one time, then exits.

set -e
cd "$(dirname "$0")"
source .venv/bin/activate
python -m sermon_processor --batch
