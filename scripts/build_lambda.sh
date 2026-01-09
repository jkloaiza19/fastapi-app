#!/usr/bin/env bash
# chmod +x scripts/build_lambda.sh
set -euo pipefail

REQ_FILE="lambda_handlers/notion_loader/requirements-lambda.txt"
BUILD_DIR="build_lambda"
OUTPUT_ZIP="notion_sync_lambda.zip"

echo "Cleaning up previous build artifacts..."
rm -rf "$BUILD_DIR" "$OUTPUT_ZIP"
mkdir -p "$BUILD_DIR/utils"

echo "Installing runtime requirements into $BUILD_DIR using Lambda-compatible Docker image..."
#docker run --rm \
#  -v "$PWD":/var/task \
#  -w /var/task \
#  public.ecr.aws/sam/build-python3.11 \
#  /bin/bash -lc "pip install -U pip && pip install -r \"$REQ_FILE\" -t \"$BUILD_DIR\" --only-binary=:all:"
docker run --rm \
  --platform linux/amd64 \
  -v "$PWD":/var/task \
  -w /var/task \
  public.ecr.aws/sam/build-python3.11 \
  /bin/bash -lc "pip install -U pip && pip install -r \"$REQ_FILE\" -t \"$BUILD_DIR\" --only-binary=:all:"
# pip install --platform manylinux2014_x86_64 --target=./package --implementation cp --python-version 3.12 --only-binary=:all: pydantic

echo "Copying lambda handler + project code..."
cp lambda_handlers/notion_loader/lambda_handler.py "$BUILD_DIR/"
cp utils/notion_loader.py "$BUILD_DIR/utils/"

# Remove caches
rm -rf "$BUILD_DIR/__pycache__" "$BUILD_DIR/utils/__pycache__"

echo "Creating ZIP: $OUTPUT_ZIP"
pushd "$BUILD_DIR" > /dev/null
zip -r9 "../$OUTPUT_ZIP" .
popd > /dev/null

echo "Built $OUTPUT_ZIP"
rm -rf $BUILD_DIR

echo "Sanity check (should be linux, not darwin):"
unzip -l "$OUTPUT_ZIP" | grep -E "_pydantic_core.*\.so" | head -n 20
