#!/bin/bash

set -e  # Exit on error
set -o pipefail  # Exit on pipeline error

echo "Starting database initialization..."

# Check if ASYNC_DATABASE_URL is set
if [ -z "$ASYNC_DATABASE_URL" ]; then
  echo "Error: ASYNC_DATABASE_URL is not set."
  exit 1
fi

echo "Installing project dependencies..."
poetry install --no-root --no-dev

echo "Running Alembic migrations..."
poetry run alembic upgrade head

echo "Database initialization completed successfully."
