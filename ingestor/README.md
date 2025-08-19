# Truffle Slack Ingestion Service

Automated Slack message ingestion and expertise extraction service, refactored into a modular FastAPI-based architecture.

## Architecture

The service is now organized into modular components:

```
ingestor/
├── main.py                    # FastAPI app with scheduler
├── config.py                  # Configuration management
├── database.py                # Database models and connection
├── models/                    # Database model definitions
├── services/
│   ├── slack_service.py       # Slack API interactions
│   ├── skill_service.py       # Skill matching using taxonomy
│   └── storage_service.py     # Database operations
├── processors/
│   ├── message_processor.py   # Message processing pipeline
│   └── classifier.py          # Expertise classification
├── schedulers/
│   └── slack_ingestion.py     # Periodic ingestion tasks
└── taxonomy.py                # Skill taxonomy (unchanged)
```

## Features

- **Automatic ingestion**: Runs every 15 minutes (configurable)
- **FastAPI web interface**: RESTful API for monitoring and manual triggers
- **Database storage**: PostgreSQL with async SQLAlchemy
- **Modular design**: Easy to scale and maintain
- **Thread-safe processing**: Uses APScheduler for reliable task scheduling

## Prerequisites

1. **PostgreSQL database** (for storing expertise data)
2. **Slack Bot Token** with appropriate permissions
3. **OpenAI API Key** (if using expertise classification)

## Setup

### 1. Database Setup

Create a PostgreSQL database and update the connection string:

```bash
# Create database
createdb truffle

# Set environment variable
export DATABASE_URL="postgresql://username:password@localhost/truffle"
```

### 2. Environment Variables

Create a `.env` file or set these environment variables:

```bash
# Required
SLACK_BOT_AUTH_TOKEN=xoxb-your-token-here
DATABASE_URL=postgresql://username:password@localhost/truffle

# Optional
OPENAI_API_KEY=sk-your-key-here          # Required if CLASSIFY_EXPERTISE=1
CLASSIFY_EXPERTISE=1                      # Enable AI expertise classification
EXTRACT_SKILLS=1                          # Enable skill extraction
CLASSIFIER_MODEL=gpt-4o                   # OpenAI model to use
```

### 3. Install Dependencies

```bash
uv sync
```

## Running the Service

### FastAPI Service (Recommended)

```bash
# Start the FastAPI service with automatic scheduling
./run_fastapi.sh

# Or manually:
uv run uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

The service will:
- Start a web server on `http://localhost:8001`
- Automatically run Slack ingestion every 15 minutes
- Create database tables if they don't exist

### Legacy Script (Backward Compatibility)

```bash
# Run once (original behavior)
./run.sh
```

## API Endpoints

- `GET /` - Service status and information
- `GET /health` - Health check with scheduler status
- `GET /jobs` - List all scheduled jobs
- `POST /trigger-ingestion` - Manually trigger ingestion

## Configuration

Edit `config.py` or use environment variables:

```python
# Scheduling
INGESTION_CRON="*/15 * * * *"  # Every 15 minutes

# Processing
EXTRACT_SKILLS=True
CLASSIFY_EXPERTISE=True

# Database
DATABASE_URL="postgresql://..."
```

## Database Schema

The service creates these tables automatically:

- `users` - Slack workspace users
- `skills` - Available skills from JSON files
- `expertise_evidence` - Raw expertise evidence from messages
- `user_skill_scores` - Pre-computed expertise scores (future)

See `doc/db-schema.sql` for the complete schema.

## Monitoring

### Health Check

```bash
curl http://localhost:8001/health
```

### Manual Ingestion

```bash
curl -X POST http://localhost:8001/trigger-ingestion
```

### View Scheduled Jobs

```bash
curl http://localhost:8001/jobs
```

## Development

### Running Tests

```bash
# (Tests to be implemented)
uv run pytest
```

### Code Quality

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .
```

## Migration from Old Version

The old `main.py` has been backed up as `main_old.py`. The new version:

1. ✅ **Stores data in PostgreSQL** instead of printing to console
2. ✅ **Runs automatically** on a schedule instead of manual execution
3. ✅ **Provides web API** for monitoring and control
4. ✅ **Modular architecture** for easier maintenance and scaling

## Future Scaling

The architecture is designed for easy scaling:

1. **Queue-based processing**: Add Redis + Celery workers
2. **Horizontal scaling**: Multiple FastAPI instances behind load balancer
3. **Vector search**: Add embeddings to PostgreSQL for semantic search

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
uv run python -c "from database import create_tables; import asyncio; asyncio.run(create_tables())"
```

### Slack API Issues

```bash
# Test Slack token
curl -H "Authorization: Bearer $SLACK_BOT_AUTH_TOKEN" https://slack.com/api/auth.test
```

### Check Logs

The service logs to stdout. For production, consider using structured logging.

## Files Changed

- ✅ **New**: Modular architecture in `services/`, `processors/`, `schedulers/`
- ✅ **Updated**: `main.py` → FastAPI application
- ✅ **Updated**: `pyproject.toml` → Added FastAPI, SQLAlchemy, APScheduler dependencies
- ✅ **Backup**: `main_old.py` → Original script preserved
- ✅ **New**: `run_fastapi.sh` → Start the service
