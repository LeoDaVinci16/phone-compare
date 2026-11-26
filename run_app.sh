#!/usr/bin/env bash
# Linux / WSL / macOS: open the app (run "conda activate phone-compare" first).
cd "$(dirname "$0")" && phone-compare --serve "$@"
