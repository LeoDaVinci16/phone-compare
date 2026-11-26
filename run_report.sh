#!/usr/bin/env bash
# Linux / WSL / macOS: generate the report (run "conda activate phone-compare" first).
cd "$(dirname "$0")" && phone-compare "$@"
