#!/usr/bin/env bash
# Sermon Audio Processor - macOS batch launcher
# Double-click this file in Finder or run it from Terminal.
# It processes supported files already sitting in inbox/ one time, then exits.

cd "$(dirname "$0")"
source .venv/bin/activate
python -m sermon_processor --batch
