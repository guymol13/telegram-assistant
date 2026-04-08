#!/bin/bash
set -e
python -m playwright install chromium --with-deps
exec python bot.py
