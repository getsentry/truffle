<img src="assets/dog-small.jpg" alt="Truffle Logo" width="120">

# Truffle

A Slack bot that helps you find the experts in your organization.

Truffle indexes your public Slack channels and assigns domains of expertise to Slack users.
You can ask Truffle to find persons of a certain skill and it will reply to with the persons in your organization that demonstrated that skill in the past.

No private channels or direct messages are read. No user messages are stored.

## System Architecture

                     ┌─────────────────────────────────────────┐
                     │              TRUFFLE SYSTEM             │
                     └─────────────────────────────────────────┘

    👥 Slack Users                                    💬 Slack Messages
         │                                                   │
         │ @mention bot                                      │ periodic ingestion
         ▼                                                   ▼
    ┌─────────────────┐                              ┌──────────────────┐
    │   Slack Bot     │                              │    Ingestor      │
    │  (Port 8003)    │                              │  (Port 8001)     │
    │                 │                              │                  │
    │ • Event parsing │                              │ • Message proc.  │
    │ • Query extract │                              │ • Skill extract  │
    │ • User replies  │                              │ • Classification │
    └─────────────────┘                              │ • Score aggreg.  │
         │                                           └──────────────────┘
         │ search request                                     │
         ▼                                                    │ stores data
    ┌─────────────────┐                                       │
    │   Expert API    │                                       │
    │  (Port 8002)    │                                       │
    │                 │                                       │
    │ • Expert search │                                       │
    │ • Skill queries │                                       │
    │ • Fast lookups  │                                       │
    └─────────────────┘                                       │
         │                                                    │
         │ reads from                                         │
         ▼                                                    ▼
    ┌─────────────────────────────────────────────────────────────────┐
    │                       Database (PostgreSQL)                     │
    │                                                                 │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
    │  │    Users    │  │   Skills    │  │  Evidence   │  │ Scores  │ │
    │  │             │  │             │  │             │  │         │ │
    │  │ • slack_id  │  │ • skill_key │  │ • user_id   │  │ • user  │ │
    │  │ • name      │  │ • name      │  │ • skill_id  │  │ • skill │ │
    │  │ • timezone  │  │ • domain    │  │ • label     │  │ • score │ │
    │  │             │  │ • aliases   │  │ • confidence│  │ • count │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────┘ │
    └─────────────────────────────────────────────────────────────────┘

    Flow:
    1. Slack messages → Ingestor → Extract skills → Store evidence
    2. Evidence → Score Aggregation → User skill scores
    3. User @mentions bot → Slack Bot → Expert API → Query scores → Reply with experts


---
Built by [Anton Pirker](https://github.com/antonpirker) during Sentry Hackweek 2025.

The truffle dog image is from [Vecteezy](https://www.vecteezy.com).
