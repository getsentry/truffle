# Skill Database Integration Plan

## Goal
Refactor the Slack Bot to use the centralized Skill database model from the ingestor service instead of hardcoded skill lists, creating a single source of truth for all skills.

## Current State Analysis

### Ingestor Service ✅
- **Database Model**: `Skill` with `skill_key`, `name`, `domain`, `aliases` (JSON)
- **Storage Service**: `get_all_skills()`, `upsert_skills()`, `get_skill_by_key()`
- **Skill Service**: `SkillMatcher` that loads from database with caching
- **Import Scripts**: JSON-based skill taxonomy import system

### Expert API ❌
- **Current**: Mock data in `/skills` endpoint
- **Needed**: Real database connectivity and queries

### Slack Bot ❌
- **Current**: Hardcoded `tech_skills` set (109 skills) in `QueryParser`
- **Needed**: Dynamic skill loading from Expert API

## Refactor Plan

### Phase 1: Expert API Database Integration

#### 1.1 Add Database Connectivity
```python
# expert_api/database/
├── __init__.py
├── models.py      # Import from ingestor models
└── session.py     # Database session management
```

#### 1.2 Update Expert API Dependencies
- Add `asyncpg`, `sqlalchemy[asyncio]` to `expert_api/pyproject.toml`
- Add database configuration to `expert_api/config.py`
- Create database connection in Expert API

#### 1.3 Replace Mock Skills Endpoint
```python
# expert_api/main.py
@app.get("/skills", response_model=SkillsResponse)
async def list_skills():
    """List all available skills from database"""
    storage = StorageService()
    db_skills = await storage.get_all_skills()

    skills = [
        SkillInfo(
            key=skill.skill_key,
            name=skill.name,
            category=skill.domain,
            aliases=json.loads(skill.aliases or "[]")
        )
        for skill in db_skills
    ]

    return SkillsResponse(
        skills=skills,
        total_count=len(skills),
        categories=sorted(set(s.category for s in skills))
    )
```

### Phase 2: Slack Bot Dynamic Skill Loading

#### 2.1 Create Skill Cache Service
```python
# slack_bot/services/skill_cache_service.py
class SkillCacheService:
    def __init__(self, expert_api_client: ExpertAPIClient):
        self.expert_api_client = expert_api_client
        self._skills_cache: dict[str, SkillInfo] = {}
        self._aliases_cache: dict[str, str] = {}
        self._last_refresh: datetime | None = None
        self._refresh_interval = timedelta(hours=1)

    async def get_all_skills(self) -> dict[str, SkillInfo]:
        """Get all skills with caching"""
        if self._needs_refresh():
            await self._refresh_skills()
        return self._skills_cache

    async def get_skills_by_text(self, text: str) -> list[str]:
        """Extract skill keys from text using aliases"""
        await self.get_all_skills()  # Ensure cache is fresh

        found_skills = []
        text_lower = text.lower()

        # Check skill names and aliases
        for alias, skill_key in self._aliases_cache.items():
            if alias in text_lower:
                found_skills.append(skill_key)

        return list(set(found_skills))  # Remove duplicates
```

#### 2.2 Update Configuration
```python
# slack_bot/config.py
class Settings(BaseSettings):
    # ... existing settings ...

    # Skill cache settings
    skill_cache_refresh_interval_hours: int = Field(default=1, alias="SKILL_CACHE_REFRESH_HOURS")
```

### Phase 3: QueryParser Refactoring

#### 3.1 Inject Skill Service
```python
# slack_bot/services/query_parser.py
class QueryParser:
    def __init__(self, skill_cache_service: SkillCacheService):
        self.skill_cache_service = skill_cache_service
        # Remove hardcoded self.tech_skills

        # Keep existing query patterns
        self.query_patterns = [...]
        self.compiled_patterns = [...]

    async def _extract_skills_from_text(self, text: str) -> list[str]:
        """Extract technology skills from text using database"""
        try:
            # Use dynamic skill loading from database
            skills = await self.skill_cache_service.get_skills_by_text(text)
            return skills
        except Exception as e:
            logger.error(f"Failed to extract skills from database: {e}")
            # Database is expected to be available - return empty list if fails
            return []
```

#### 3.2 Update Service Initialization
```python
# slack_bot/main.py
# Initialize services with dependency injection
event_processor = EventProcessor(bot_user_id=None)
expert_api_client = ExpertAPIClient(base_url=settings.expert_api_url)
skill_cache_service = SkillCacheService(expert_api_client)
query_parser = QueryParser(skill_cache_service)

# Update event processor to use new query parser
event_processor.query_parser = query_parser
```

### Phase 4: Enhanced Features

#### 4.1 Skill Management Endpoints
```python
# slack_bot/main.py
@app.post("/admin/skills/refresh")
async def refresh_skills():
    """Force refresh skill cache"""
    await skill_cache_service.refresh_skills()
    return {"status": "Skills cache refreshed"}

@app.get("/admin/skills/stats")
async def skill_stats():
    """Get skill cache statistics"""
    return {
        "total_skills": len(skill_cache_service._skills_cache),
        "last_refresh": skill_cache_service._last_refresh,
        "cache_age_minutes": skill_cache_service._get_cache_age_minutes()
    }
```

#### 4.2 Health Monitoring
```python
# slack_bot/main.py - Update debug/stats endpoint
@app.get("/debug/stats")
async def debug_stats():
    stats = event_processor.get_processing_stats()
    skill_stats = await skill_cache_service.get_stats()

    return {
        "service": "Truffle Slack Bot",
        "processing_stats": stats,
        "skill_cache_stats": skill_stats,
        "expert_api_status": "available" if await expert_api_client.is_available() else "unavailable"
    }
```

## Implementation Strategy

### Step 1: Expert API Database Connection (30 mins)
1. Add database dependencies to Expert API
2. Create database models and session
3. Replace mock `/skills` endpoint with real queries

### Step 2: Skill Cache Service (45 mins)
1. Create `SkillCacheService` with caching and refresh logic
2. Implement skill text extraction with aliases
3. Add error handling and logging

### Step 3: QueryParser Refactoring (30 mins)
1. Remove hardcoded `tech_skills`
2. Inject `SkillCacheService`
3. Update skill extraction to use dynamic loading

### Step 4: Integration Testing (30 mins)
1. Test skill loading from database
2. Test skill extraction with real data
3. Test error handling for API failures
4. Verify end-to-end Slack bot functionality

### Step 5: Enhanced Features (45 mins)
1. Add admin endpoints for skill management
2. Implement health monitoring
3. Add comprehensive logging and metrics

## Benefits

### Immediate Benefits
- **Single Source of Truth**: All skills managed in database
- **Dynamic Updates**: New skills added without code changes
- **Consistency**: All services use same skill definitions
- **Scalability**: Skills can be managed via API

### Long-term Benefits
- **Skill Analytics**: Track skill usage and popularity
- **Advanced Matching**: Leverage database for fuzzy matching
- **Skill Relationships**: Model skill hierarchies and dependencies
- **Multi-language Support**: Internationalized skill names and aliases

## Rollback Plan
- Comprehensive error logging for debugging issues
- Expert API health checks to detect problems early
- Database connection monitoring and alerts
- Ability to restart services to clear cache issues

## Success Metrics
- ✅ All existing queries work with database skills
- ✅ New skills added to database are immediately available
- ✅ Skill extraction handles errors gracefully (logs issues, returns empty)
- ✅ Performance impact < 50ms per query
- ✅ Zero downtime deployment
