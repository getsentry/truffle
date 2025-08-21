# Docker Deployment Guide

This repository uses a multi-service Docker setup where a single Dockerfile can run any of the three Truffle services based on environment variables.

## Quick Start

```bash
# Build the image
docker build -t truffle .

# Run individual services
docker run -e SERVICE_NAME=slack_bot -p 3001:8000 truffle
docker run -e SERVICE_NAME=ingestor -p 3002:8000 truffle
docker run -e SERVICE_NAME=expert_api -p 3003:8000 truffle

# Or use docker-compose to run all services
docker-compose up
```

## Architecture

- **Single Dockerfile**: Installs dependencies for all services
- **Environment-based selection**: `SERVICE_NAME` determines which service runs
- **Independent scaling**: Deploy multiple containers of the same service
- **Shared base image**: Reduces total image size and maintenance

## Environment Variables

### Required for all services:
- `SERVICE_NAME`: `slack_bot`, `ingestor`, or `expert_api`

### Service-specific variables:

**Slack Bot:**
- `SLACK_BOT_HOST=0.0.0.0`
- `SLACK_BOT_PORT=8000`
- `SLACK_BOT_AUTH_TOKEN=xoxb-your-token`
- `EXPERT_API_URL=http://expert-api:8000`

**Ingestor:**
- `INGESTOR_HOST=0.0.0.0`
- `INGESTOR_PORT=8000`
- `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db`
- `SLACK_API_TOKEN=xoxp-your-token`
- `OPENAI_API_KEY=sk-your-key`
- `INGESTION_CRON=0 */6 * * *`

**Expert API:**
- `EXPERT_API_HOST=0.0.0.0`
- `EXPERT_API_PORT=8000`
- `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db`

### Optional (all services):
- `SENTRY_DSN=https://your-sentry-dsn`
- `LOG_LEVEL=INFO`
- `DEBUG=false`

## Production Deployment

### Using Docker Compose

1. Copy `docker-compose.yml` and customize environment variables
2. Create `.env` file with sensitive values:
   ```bash
   SLACK_BOT_AUTH_TOKEN=xoxb-your-token
   SLACK_API_TOKEN=xoxp-your-token
   OPENAI_API_KEY=sk-your-key
   SENTRY_DSN=https://your-sentry-dsn
   POSTGRES_PASSWORD=secure-password
   ```
3. Deploy: `docker-compose up -d`

### Using Container Orchestration

For Kubernetes, create separate deployments:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: truffle-slack-bot
spec:
  replicas: 2
  selector:
    matchLabels:
      app: truffle-slack-bot
  template:
    metadata:
      labels:
        app: truffle-slack-bot
    spec:
      containers:
      - name: slack-bot
        image: truffle:latest
        env:
        - name: SERVICE_NAME
          value: "slack_bot"
        # ... other env vars
```

## Health Checks

All services expose `/health` endpoints on their respective ports for monitoring and load balancer health checks.

## Building and Optimization

The Dockerfile uses:
- Python 3.13 slim base image
- `uv` for faster package installation
- Multi-stage approach for dependency optimization
- `.dockerignore` to exclude unnecessary files

## Scaling Considerations

- **Slack Bot**: Can run multiple replicas behind a load balancer
- **Expert API**: Stateless, scales horizontally
- **Ingestor**: Single instance recommended (scheduled jobs), or use external job queue for scaling
