#!/bin/sh
# SCEMAS — Container entrypoint
#
# Runs after the Docker volume is mounted, so /app/shared contains the
# real shared package. Installs it as an editable package so Python can
# resolve `from shared import ...` imports, then starts the service.

set -e

echo "Upgrading build tools"
pip install --upgrade pip setuptools wheel
echo "Installing shared package from mounted volume..."
pip install /app/shared --quiet

echo "Starting service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload