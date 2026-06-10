#!/usr/bin/env bash
# build.sh — runs on every deploy on Railway/Render
# Make this executable: chmod +x build.sh

set -e  # Exit immediately if any command fails

echo "=== Installing dependencies ==="
pip install -r requirements.txt

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running migrations ==="
python manage.py migrate --noinput

echo "=== Build complete ==="
