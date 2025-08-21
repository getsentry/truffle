<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle Slack Bot

The Slack Bot provides the interactive interface for Truffle, responding to user mentions in Slack channels with expert recommendations. When users mention the bot with queries about specific skills or technologies, it parses the request, searches for relevant experts using the Expert API, and replies with formatted recommendations. The bot enables seamless expert discovery directly within Slack conversations, making organizational knowledge instantly accessible to team members.

## Configuration

Configure the service by setting these environment variables:

### Required
- `SLACK_BOT_AUTH_TOKEN` - Slack Bot OAuth token (xoxb-...)

### Optional
- `DEBUG` - Enable debug mode (default: `false`)
- `EXPERT_API_URL` - Expert API endpoint (default: `http://localhost:8002`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `SLACK_BOT_HOST` - Server host (default: `0.0.0.0`)
- `SLACK_BOT_PORT` - Server port (default: `8003`)
- `SLACK_BOT_SENTRY_DSN` - Sentry DSN for error tracking

### Example
```bash
export SLACK_BOT_AUTH_TOKEN=xoxb-your-token-here
export SLACK_BOT_PORT=8003
export EXPERT_API_URL=http://expert-api:8000
```

---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
