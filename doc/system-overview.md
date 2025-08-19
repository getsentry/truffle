### Truffle Slack Expertise System – Current Architecture Overview

This document summarizes the system as implemented today so an LLM can understand the current components, data flow, and conventions.

## Purpose
Identify who knows what inside Slack by:
- Matching messages to a hard-coded taxonomy of skills/domains
- Classifying whether a message demonstrates the author’s expertise for each matched skill

## Components
- ingest_slack
  - `main.py`: pulls channels, users, and public channel messages (incl. thread replies); prints enriched output.
  - `taxonomy.py`: hard-coded taxonomy covering engineering (incl. Sentry JS guides, Python integrations), SaaS business topics, and Sentry product topics. Provides `SkillMatcher`.
  - `classifier.py`: GPT-4o-based expertise classifier with strict JSON output.

## Environment flags and config
- `SLACK_BOT_AUTH_TOKEN`: Slack token (required)
- `OPENAI_API_KEY`: OpenAI API key (required if `CLASSIFY_EXPERTISE=1`)
- `CLASSIFIER_MODEL` (optional): defaults to `gpt-4o`
- `EXTRACT_SKILLS=1`: enable taxonomy matching and printing of skills per message
- `CLASSIFY_EXPERTISE=1`: enable LLM-based expertise classification for matched skills

## Data flow (runtime)
1. List public channels the bot is in and workspace users (filters bots/deleted).
2. Stream messages per channel; also fetch and emit thread replies.
3. Replace Slack mentions like `<@U123>` with `@name[slack_user_id:U123]` for readability.
4. If `EXTRACT_SKILLS=1`: run `SkillMatcher.match_text(...)` on each message.
   - For thread parents, cache `{thread_ts -> {text, skills}}`.
   - For replies, inherit parent thread skills and keep `parent_text` for classification context.
5. If `CLASSIFY_EXPERTISE=1`: call the classifier per message with any (inherited + direct) skills.
6. Print results to stdout.

## Taxonomy (high level)
- Domains: `engineering`, `devops`, `data`, `product`, `design`, `marketing`, `sales`, `customer_success`, `sentry`.
- Engineering includes major languages/runtimes/frameworks (e.g., JavaScript + React, Next.js, Node, Express, Angular, Vue, Svelte/SvelteKit, Remix, Nuxt, Gatsby, Astro, Preact, Solid/SolidStart, Ember, Electron, Deno, Bun, Cloudflare Workers; TypeScript; plus Sentry Python integrations like Django/Flask/FastAPI, SQLAlchemy, Redis, Celery, Airflow, etc.).
- Business includes SEO/SEM, content, automation, growth, analytics, sales (Salesforce/HubSpot), product management, design, data/BI.
- Sentry product topics include alerts, dashboards, discover/logs/profiling/session replay, insights, issues, releases, relay, uptime monitoring, user feedback, security/legal/PII, and more.

## Matcher
- `SkillMatcher` performs alias-based, case-insensitive, boundary-aware matching.
- Output: list of `skill_keys` per message.

## Expertise classifier
- Model: OpenAI `gpt-4o` in JSON mode.
- Input per message:
  - `author_id`, `channel_id`, `message_id`
  - `text` (the message)
  - `parent_text` (for replies, if available)
  - `skill_keys` (union of direct matches + inherited parent thread skills)
- Instruction enforces: return ONLY a JSON object (no code fences or prose).
- Output JSON schema:
```json
{
  "results": [
    {
      "skill_key": "<string>",
      "label": "positive_expertise | negative_expertise | neutral",
      "confidence": 0.0,
      "rationale": "<short string>"
    }
  ]
}
```

## Thread handling
- For a reply, the system inherits the parent message’s skills and passes `parent_text` to the classifier. This lets short replies like “I can help” be attributed to the skill mentioned in the thread parent (e.g., Nuxt).

## Running
```bash
export SLACK_BOT_AUTH_TOKEN=...        # required
export EXTRACT_SKILLS=1                # enable skill matching
export CLASSIFY_EXPERTISE=1            # enable LLM classification
export OPENAI_API_KEY=...              # required with classification
cd truffle/ingest_slack
./run.sh
```

## Current outputs
- Console logs of:
  - Channels and users
  - Messages (with mention replacements)
  - Detected skills per message
  - Expertise labels and confidences per skill when classification is enabled

## Current limitations / next steps
- No persistence yet (evidence or scores are not stored); only console output.
- No aggregation/scoring of users by skill; not exposed via Slack bot commands.
- No batching/caching for classifier requests (MVP sends one message at a time).

## Key files (paths relative to workspace root)
- `truffle/ingest_slack/main.py`
- `truffle/ingest_slack/taxonomy.py`
- `truffle/ingest_slack/classifier.py`
