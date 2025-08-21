<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle Expert API Service

The Expert API Service provides fast, read-only access to expert search functionality for the Truffle system. It offers RESTful endpoints for querying user expertise based on skills, technologies, or domains, with support for confidence filtering, time-based relevance, and flexible search strategies. The API serves as the backend for both the Slack Bot and any future integrations, delivering expert recommendations.

## Configuration

Configure the service by setting these environment variables:

### Required
- `TRUFFLE_DB_URL` - PostgreSQL database URL

### Optional
- `DEBUG` - Enable debug mode (default: `false`)
- `DEBUG_SQL` - Enable SQL query logging (default: `false`)
- `EXPERT_API_HOST` - Server host (default: `0.0.0.0`)
- `EXPERT_API_PORT` - Server port (default: `8002`)
- `EXPERT_API_SENTRY_DSN` - Sentry DSN for error tracking
- `LOG_LEVEL` - Logging level (default: `INFO`)

### Example
```bash
export TRUFFLE_DB_URL=postgresql://user:pass@postgres:5432/truffle
export EXPERT_API_PORT=8002

```

---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
