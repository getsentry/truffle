<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle Ingestor Service

The Ingestor Service is the core data processing component of Truffle that automatically analyzes Slack conversations to identify user expertise. It periodically ingests messages from public Slack channels, extracts mentioned skills and technologies, classifies the level of expertise demonstrated in each message, and maintains aggregated skill scores for users. The service handles the complete pipeline from message collection to expertise evidence storage, enabling the system to build a comprehensive map of organizational knowledge and expertise.

## Configuration

Configure the service by setting these environment variables:

### Required
- `OPENAI_API_KEY` - OpenAI API key for AI processing
- `SLACK_BOT_AUTH_TOKEN` - Slack Bot OAuth token (xoxb-...)
- `TRUFFLE_DB_URL` - PostgreSQL database URL

### Optional
- `DEBUG` - Enable debug mode (default: `false`)
- `INGESTOR_HOST` - Server host (default: `0.0.0.0`)
- `INGESTOR_PORT` - Server port (default: `8001`)
- `INGESTOR_SENTRY_DSN` - Sentry DSN for error tracking
- `LOG_LEVEL` - Logging level (default: `INFO`)

### Example
```bash
export TRUFFLE_DB_URL=postgresql://user:pass@postgres:5432/truffle
export SLACK_BOT_AUTH_TOKEN=xoxb-your-token-here
export OPENAI_API_KEY=sk-your-openai-key


```

---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
