# Deployment Guide

This guide covers deploying the FastAPI application to various environments.

## Table of Contents
- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [AWS Lambda (Zappa)](#aws-lambda-zappa)
- [AWS ECS/Fargate](#aws-ecsfargate)
- [Environment Configuration](#environment-configuration)

## Local Development

### Prerequisites
- Python 3.11+
- Poetry
- PostgreSQL
- Redis

### Setup
```bash
# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Development Server Options
```bash
# With auto-reload
poetry run uvicorn main:app --reload

# With specific host and port
poetry run uvicorn main:app --host 0.0.0.0 --port 8080

# With workers (production-like)
poetry run gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

## Docker Deployment

### Using Docker Compose (Recommended for Development)

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

The `docker-compose.yml` includes:
- FastAPI application
- PostgreSQL database
- Redis cache
- Volume mounts for persistence

### Standalone Docker

```bash
# Build image
docker build -t fastapi-app:latest .

# Run container
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name fastapi-app \
  fastapi-app:latest

# View logs
docker logs -f fastapi-app

# Stop container
docker stop fastapi-app
```

### Multi-stage Docker Build

The Dockerfile uses multi-stage builds for optimization:
1. **Builder stage**: Installs dependencies
2. **Runtime stage**: Contains only runtime requirements

Benefits:
- Smaller image size
- Faster deployments
- Better security (no build tools in production)

## AWS Lambda (Zappa)

### Initial Setup

1. **Configure AWS credentials**
```bash
aws configure
# Enter your AWS Access Key ID, Secret Access Key, and region
```

2. **Initialize Zappa**
```bash
poetry run zappa init
```

This creates `zappa_settings.json` with your configuration.

### Deployment

```bash
# First deployment
poetry run zappa deploy production

# Update existing deployment
poetry run zappa update production

# View logs
poetry run zappa tail production

# Undeploy
poetry run zappa undeploy production
```

### Zappa Configuration (`zappa_settings.json`)

```json
{
  "production": {
    "app_function": "main.handler",
    "aws_region": "us-east-1",
    "profile_name": "default",
    "project_name": "fastapi-app",
    "runtime": "python3.11",
    "s3_bucket": "your-zappa-deployments-bucket",
    "environment_variables": {
      "ENVIRONMENT": "production"
    },
    "vpc_config": {
      "SubnetIds": ["subnet-xxxxx", "subnet-yyyyy"],
      "SecurityGroupIds": ["sg-xxxxx"]
    },
    "aws_environment_variables": {
      "DATABASE_URL": "arn:aws:secretsmanager:region:account:secret:db-url",
      "REDIS_URL": "arn:aws:secretsmanager:region:account:secret:redis-url"
    }
  }
}
```

### Lambda Considerations

**Limitations:**
- 15-minute timeout (consider async processing for long tasks)
- 10GB memory limit
- Cold starts (use provisioned concurrency if needed)

**Best Practices:**
- Use AWS Secrets Manager for sensitive data
- Connect to RDS via VPC
- Use ElastiCache for Redis
- Implement proper error handling
- Set up CloudWatch alarms

## AWS ECS/Fargate

### Using CloudFormation

The `cloudformation/infra.yml` template includes:
- ECS Cluster
- Fargate Service
- Application Load Balancer
- Auto-scaling configuration

### Deploy Infrastructure

```bash
# Deploy the stack
aws cloudformation create-stack \
  --stack-name fastapi-app-infra \
  --template-body file://cloudformation/infra.yml \
  --parameters \
    ParameterKey=Environment,ParameterValue=production \
    ParameterKey=DatabaseURL,ParameterValue=your-db-url \
  --capabilities CAPABILITY_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name fastapi-app-infra

# Update stack
aws cloudformation update-stack \
  --stack-name fastapi-app-infra \
  --template-body file://cloudformation/infra.yml \
  --parameters <same-as-create>
```

### Build and Push Docker Image

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t fastapi-app:latest .

# Tag for ECR
docker tag fastapi-app:latest \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-app:latest

# Push to ECR
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/fastapi-app:latest
```

### Update ECS Service

```bash
# Force new deployment
aws ecs update-service \
  --cluster fastapi-app-cluster \
  --service fastapi-app-service \
  --force-new-deployment
```

## Environment Configuration

### Development (.env)
```bash
ENVIRONMENT=dev
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
REDIS_URL=redis://localhost:6379
DEBUG=true
LOG_LEVEL=DEBUG
```

### Staging
```bash
ENVIRONMENT=staging
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/dbname
REDIS_URL=redis://staging-redis:6379
DEBUG=false
LOG_LEVEL=INFO
SENTRY_DNS=https://your-sentry-dsn
```

### Production
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/dbname
REDIS_URL=redis://prod-redis:6379
DEBUG=false
LOG_LEVEL=WARNING
SENTRY_DNS=https://your-sentry-dsn
API_KEYS=key1,key2,key3
SECRET_KEY=your-production-secret-key
```

## Database Migrations in Production

### Running Migrations

**Before deployment:**
```bash
# Test migrations locally
poetry run alembic upgrade head

# Check migration status
poetry run alembic current
```

**In AWS Lambda:**
```bash
# SSH into Lambda environment or use a separate migration Lambda
poetry run zappa manage production "alembic upgrade head"
```

**In ECS:**
```bash
# Run as a one-off task
aws ecs run-task \
  --cluster fastapi-app-cluster \
  --task-definition fastapi-app-migration \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

### Migration Best Practices

1. **Always backup before migrations**
```bash
# PostgreSQL
pg_dump -h hostname -U username dbname > backup.sql
```

2. **Test migrations on staging first**

3. **Use blue-green deployment for zero-downtime**

4. **Keep migrations backward compatible when possible**

## Monitoring and Logging

### CloudWatch Logs

Logs are automatically sent to CloudWatch when deployed to AWS.

```bash
# View logs (Zappa)
poetry run zappa tail production --since 1h

# View logs (ECS)
aws logs tail /ecs/fastapi-app --follow
```

### Sentry Integration

Already configured in `main.py`. Set `SENTRY_DNS` in environment variables.

Features:
- Error tracking
- Performance monitoring
- Release tracking

### Health Checks

Endpoint: `GET /healthcheck`

Configure in load balancer:
```yaml
HealthCheck:
  Path: /healthcheck
  Interval: 30
  Timeout: 5
  HealthyThreshold: 2
  UnhealthyThreshold: 3
```

## Scaling

### Auto-scaling Configuration (ECS)

```yaml
ScalingPolicy:
  Type: TargetTrackingScaling
  TargetValue: 70.0  # CPU utilization
  ScaleInCooldown: 300
  ScaleOutCooldown: 60
```

### Lambda Concurrent Executions

```bash
# Set reserved concurrent executions
aws lambda put-function-concurrency \
  --function-name fastapi-app-production \
  --reserved-concurrent-executions 100
```

### Database Connection Pooling

Already configured in `db/database.py`:
- Pool size: 5
- Max overflow: 10
- Pool timeout: 30s

Adjust based on your needs and RDS instance limits.

## CI/CD Pipeline

### Using AWS CodeBuild

The `buildspec.yml` includes:
1. Install dependencies
2. Run tests
3. Build Docker image
4. Push to ECR
5. Deploy to ECS

### GitHub Actions Example

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Build and push Docker image
        run: |
          docker build -t fastapi-app .
          # ... push to ECR
      
      - name: Deploy to ECS
        run: |
          aws ecs update-service \
            --cluster fastapi-app-cluster \
            --service fastapi-app-service \
            --force-new-deployment
```

## Security Checklist

- [ ] All environment variables stored in AWS Secrets Manager
- [ ] Database credentials rotated regularly
- [ ] API keys rotated regularly
- [ ] SSL/TLS certificates configured
- [ ] Security groups properly configured
- [ ] IAM roles follow least privilege principle
- [ ] Sentry configured for error tracking
- [ ] CloudWatch alarms set up
- [ ] Backup strategy in place
- [ ] DDoS protection enabled (AWS Shield)
- [ ] WAF rules configured if needed

## Troubleshooting

### Common Issues

**Issue: Lambda timeout**
- Solution: Increase timeout in `zappa_settings.json` or move long tasks to async processing

**Issue: Database connection errors**
- Check VPC configuration
- Verify security groups allow traffic
- Check connection pool settings

**Issue: Out of memory**
- Increase Lambda memory or ECS task memory
- Check for memory leaks
- Optimize image processing settings

**Issue: Cold starts**
- Use provisioned concurrency (Lambda)
- Implement health check warming
- Consider ECS for consistent performance

## Support

For deployment issues:
1. Check CloudWatch logs
2. Review Sentry errors
3. Verify environment variables
4. Check AWS service status
5. Contact support: jkloaiza19@gmail.com
