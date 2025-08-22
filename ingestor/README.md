<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle Ingestor Service

The Ingestor Service is the core data processing component of Truffle that automatically analyzes Slack conversations to identify user expertise. It periodically ingests messages from public Slack channels, extracts mentioned skills and technologies, classifies the level of expertise demonstrated in each message, and maintains aggregated skill scores for users. The service handles the complete pipeline from message collection to expertise evidence storage, enabling the system to build a comprehensive map of organizational knowledge and expertise.

## Web Management API

The Ingestor provides web endpoints for database and import management:

### Database Operations
- `POST /database/reset?import_skills=true` - Reset database (drop and recreate all tables) ⚡ Fast
- `POST /database/reset-and-reimport` - Full reset + reimport all Slack history (30 days) 🔄 Background
- `POST /slack/reimport` - Reimport full Slack history without database reset 🔄 Background

**Note**: Long-running operations (reimport/reset-and-reimport) return immediately and run in background to prevent HTTP timeouts.

### Monitoring & Status
- `GET /` - Service status with queue statistics
- `GET /health` - Health check with scheduler status
- `GET /queue/stats` - Current message queue statistics
- `GET /workers/stats` - Background worker status and performance
- `POST /queue/clear` - Clear completed tasks from processing queue

## Configuration

Configure the service by setting these environment variables:

### Required
- `OPENAI_API_KEY` - OpenAI API key for AI processing
- `SLACK_BOT_AUTH_TOKEN` - Slack Bot OAuth token (xoxb-...)
- `TRUFFLE_DB_URL` - PostgreSQL database URL

### Optional
- `DEBUG` - Enable debug mode (default: `false`)
- `DEBUG_SQL` - Enable SQL query logging (default: `false`)
- `INGESTOR_HOST` - Server host (default: `0.0.0.0`)
- `INGESTOR_PORT` - Server port (default: `8001`)
- `INGESTOR_SENTRY_DSN` - Sentry DSN for error tracking
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `SLACK_API_DELAY` - Delay between Slack API calls in seconds (default: `1.2`)
- `SLACK_BATCH_SIZE` - Number of API requests per batch (default: `50`)
- `SLACK_BATCH_WAIT_SECONDS` - Seconds to wait between batches (default: `61`)

### Example
```bash
export TRUFFLE_DB_URL=postgresql://user:pass@postgres:5432/truffle
export SLACK_BOT_AUTH_TOKEN=xoxb-your-token-here
export OPENAI_API_KEY=sk-your-openai-key


```

---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
