Notion -> Astra Lambda

This folder contains a CloudFormation template and build instructions to package
and deploy a Lambda function that runs your project's Notion->Astra sync
(`utils.notion_loader.run_sync`).

Build steps (local)

1. From the `fastapi-app` directory, install build-time deps if necessary and run the build script:

```bash
cd /path/to/projects/fastapi-app
./scripts/build_lambda.sh
# This produces notion_sync_lambda.zip in the fastapi-app directory
```

2. Upload zip to S3

```bash
aws s3 cp notion_sync_lambda.zip s3://<bucket>/path/notion_sync_lambda.zip
```

Deploy using CloudFormation

```bash
aws cloudformation deploy \
  --template-file cloudformation/notion_sync_lambda.yml \
  --stack-name notion-sync-stack \
  --parameter-overrides \
      ArtifactS3Bucket=<bucket> \
      ArtifactS3Key=path/notion_sync_lambda.zip \
      NotionToken=<notion-token> \
      NotionDatabaseId=<database-id> \
      OpenAIKey=<openai-key> \
      AstraToken=<astra-token> \
      AstraEndpoint=<astra-endpoint-url>
```

Notes and recommendations

- Make sure secrets are stored safely (Secrets Manager or SSM Parameter Store) rather than passing them directly as CloudFormation parameters.
- You may want to split environment variables into an external file and reference them via SSM/Secrets Manager in CloudFormation.
- Increase Lambda memory/timeout if syncing many pages.
- Consider using an event source (CloudWatch scheduled event / EventBridge) to run this periodically.
- For long-running syncs or heavy embedding usage, consider moving embeddings off-Lambda (e.g., to an ECS job) to avoid cold-starts and ephemeral quota issues.

