#!/bin/bash
# chmod +x scripts/build_lambda.sh

SECRET_NAME="fastapi-dev-secrets"
REGION="us-east-1"
ENV_FILE="../.env"
# Read the .env file and convert it to a JSON string
#JSON_STRING=$(cat $ENV_FILE | awk -F'=' '{printf "\"%s\":\"%s\",", $1, $2}' | sed 's/,$//')
JSON_STRING=$(grep -v '^#' "$ENV_FILE" | grep -v '^$' | awk -F'=' '{printf "\"%s\":\"%s\",", $1, $2}' | sed 's/,$//')
JSON_STRING="{${JSON_STRING}}"

# Upload the JSON string to AWS Secrets Manager
aws secretsmanager put-secret-value --secret-id "$SECRET_NAME" --secret-string "$JSON_STRING" --region "$REGION"
