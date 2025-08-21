<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle Slack Bot

The Slack Bot provides the interactive interface for Truffle, responding to user mentions in Slack channels with expert recommendations. When users mention the bot with queries about specific skills or technologies, it parses the request, searches for relevant experts using the Expert API, and replies with formatted recommendations. The bot enables seamless expert discovery directly within Slack conversations, making organizational knowledge instantly accessible to team members.

## Configuration

Configure the service by setting these environment variables:

### Required
- `SLACK_BOT_AUTH_TOKEN` - Slack Bot OAuth token (xoxb-...)

### For Multi-Workspace Distribution (Optional)
- `SLACK_CLIENT_ID` - Slack app client ID (for OAuth installations)
- `SLACK_CLIENT_SECRET` - Slack app client secret (for OAuth installations)

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

# For multi-workspace distribution:
export SLACK_CLIENT_ID=your-client-id
export SLACK_CLIENT_SECRET=your-client-secret
```

### Multi-Workspace Setup
1. **Enable App Distribution** in your Slack app settings
2. **Set redirect URL** to `https://your-domain.com/slack/oauth`
3. **Configure OAuth credentials** using environment variables above
4. **Share installation link** with other workspace admins

---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
