#!/usr/bin/env bash
set -euo pipefail

# Build a Lambda deployment package zip for the Notion->Astra sync function.
# Run this from the project root: /path/to/projects/fastapi-app

REQ_FILE="lambda_handlers/notion_loader/requirements-lambda.txt"
BUILD_DIR="build_lambda"
OUTPUT_ZIP="notion_sync_lambda.zip"

echo "Cleaning up previous build artifacts..."
rm -rf "$BUILD_DIR" "$OUTPUT_ZIP" .venv_lambda
mkdir -p "$BUILD_DIR"
mkdir -p "$BUILD_DIR/utils"

# Create a temporary virtualenv to ensure pip and wheel are available
#python3 -m venv .venv_lambda
#source .venv_lambda/bin/activate
python -m pip install --upgrade pip wheel

echo "Installing runtime requirements into $BUILD_DIR..."
# Install only runtime dependencies into the build directory
# pip install --upgrade pip && pip install -r requirements.txt -t build/python --only-binary=:all:
docker run --rm -v "$PWD":/var/task public.ecr.aws/sam/build-python3.11
pip install --upgrade pip && pip install -r "$REQ_FILE" -t "$BUILD_DIR" --only-binary=:all:

# Copy project code into the build directory. Exclude .env, git, venvs, tests and large artifacts.
# Adjust the rsync include/exclude list if you want a narrower footprint.
cp lambda_handlers/notion_loader/lambda_handler.py "$BUILD_DIR/"
cp utils/notion_loader.py "$BUILD_DIR/utils"
#echo "Copying project files..."
#rsync -a --prune-empty-dirs \
#  --exclude '.venv' \
#  --exclude '.venv_lambda' \
#  --exclude '.git' \
#  --exclude '__pycache__' \
#  --exclude 'tests' \
#  --exclude '*.pyc' \
#  --exclude '.env' \
#  --exclude 'node_modules' \
#  --exclude 'build_lambda' \
#  ./ "$BUILD_DIR/"

# Remove any virtualenvs or caches that accidentally got copied
rm -rf "$BUILD_DIR/.venv" "$BUILD_DIR/.venv_lambda" "$BUILD_DIR/__pycache__"

# Create the zip. Lambda requires files at the root of the zip
echo "Creating ZIP: $OUTPUT_ZIP"
pushd "$BUILD_DIR" > /dev/null
zip -r9 "../$OUTPUT_ZIP" .
popd > /dev/null

# Cleanup local venv and artifacts used for building
deactivate || true
rm -rf .venv_lambda
rm -rf "$BUILD_DIR"

echo "Built $OUTPUT_ZIP"

# unzip -l notion_sync_lambda.zip | grep -E "pydantic_core|_pydantic_core" | head -n 20
