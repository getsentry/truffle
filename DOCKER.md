# Docker Deployment Guide

This repository uses a multi-service Docker setup where a single Dockerfile can run any of the three Truffle services based on environment variables.

## Quick Start

```bash
# Build the multi-architecture image locally
docker buildx build --platform linux/amd64,linux/arm64 -t truffle --load .

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
- **Multi-stage builds**: Build dependencies separate from runtime (45-50% size reduction)
- **Alpine Linux base**: Python 3.13-alpine (~75MB smaller than slim)
- **Multi-architecture support**: Builds for both AMD64 (servers) and ARM64 (Apple Silicon)
- **Security hardening**: Non-root user, minimal runtime dependencies
- **Fast package installation**: `uv` for optimized Python package management
- **Layer optimization**: Optimal caching and `.dockerignore` exclusions

## Scaling Considerations

- **Slack Bot**: Can run multiple replicas behind a load balancer
- **Expert API**: Stateless, scales horizontally
- **Ingestor**: Single instance recommended (scheduled jobs), or use external job queue for scaling

## How to Deploy Container to ghcr.io

### 1. Setup Multi-Architecture Builder

```bash
# Create a buildx builder for multi-architecture builds
docker buildx create --use --name truffle-builder

# Verify builder supports multiple platforms
docker buildx inspect truffle-builder --bootstrap
```

### 2. Authenticate with GitHub Container Registry

Create a GitHub Personal Access Token with `write:packages` and `read:packages` scopes:

```bash
# Set your GitHub token (can be added to .envrc)
export GITHUB_TOKEN=ghp_your_token_here

# Login to ghcr.io
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### 3. Build and Push Multi-Architecture Image

```bash
# Build for both AMD64 (servers) and ARM64 (Apple Silicon) and push
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/ORGANIZATION/truffle:latest \
  --push .

# Example:
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t ghcr.io/getsentry/truffle:latest \
  --push .
```

### 4. Verify Multi-Architecture Image

```bash
# Check that both architectures are available
docker buildx imagetools inspect ghcr.io/ORGANIZATION/truffle:latest
```

### 6. Use Published Image in Docker Compose

Update your `docker-compose.yml` to use the published image instead of building locally:

```yaml
services:
  slack-bot:
    image: ghcr.io/ORGANIZATION/truffle:latest
    # Remove: build: .
    environment:
      - SERVICE_NAME=slack_bot
      # ... other env vars
```

### 7. Make Repository Package Public (Optional)

- Go to your GitHub repository → Packages → truffle
- Change package visibility to public if needed
- This allows others to pull without authentication

### 8. Automated Multi-Architecture Publishing

For CI/CD, add this to your GitHub Actions workflow:

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v3

- name: Login to GitHub Container Registry
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}

- name: Build and push multi-architecture image
  uses: docker/build-push-action@v5
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ghcr.io/${{ github.repository }}:latest
```

## Platform Compatibility

- **AMD64 (x86_64)**: For production servers, Railway, AWS, GCP, Azure
- **ARM64 (aarch64)**: For Apple Silicon Macs, AWS Graviton, newer ARM servers
- **Automatic selection**: Docker automatically pulls the correct architecture

## Image Size Optimization

The optimized Dockerfile provides significant size reductions:

- **Before optimization**: ~720MB (single-stage, Python slim, all dependencies)
- **After optimization**: ~350-400MB (45-50% reduction)

### Optimization Techniques Applied:

1. **Multi-stage builds**: Build dependencies removed from final image
2. **Alpine Linux base**: ~75MB smaller than Python slim
3. **Non-root user**: Security hardening with minimal overhead
4. **Optimized layer caching**: Dependencies installed before source code
5. **Production-only packages**: Dev dependencies excluded
6. **Efficient package manager**: `uv` for faster, smaller installs

### Build Cache Optimization:

```bash
# Dependencies change rarely - cached layer
COPY */pyproject.toml ./*/
RUN uv pip install -e .

# Source code changes frequently - separate layer
COPY src/ ./src/
```

This ensures dependency layers are cached and only rebuilt when `pyproject.toml` files change.
