from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

# High-level domains relevant to a SaaS company
DOMAINS: list[str] = [
    "engineering",
    "devops",
    "data",
    "product",
    "design",
    "marketing",
    "sales",
    "customer_success",
    "sentry",
]


@dataclass(frozen=True)
class Skill:
    key: str
    name: str
    domain: str
    aliases: tuple[str, ...]


def _aliases(*names: str) -> tuple[str, ...]:
    # Normalize aliases for matching: lowercase, strip
    return tuple(sorted({n.strip().lower() for n in names if n and n.strip()}))


# Engineering skills based on Sentry "All SDKs Supported" list
# Reference: https://docs.sentry.io/
ENGINEERING_SDK_SKILLS: list[Skill] = [
    Skill(
        "android",
        "Android",
        "engineering",
        _aliases("android", "kotlin android", "java android"),
    ),
    Skill(
        "apple",
        "Apple (iOS/macOS)",
        "engineering",
        _aliases("apple", "ios", "macos", "swift", "objective-c", "objc"),
    ),
    Skill("dart", "Dart", "engineering", _aliases("dart")),
    Skill("elixir", "Elixir", "engineering", _aliases("elixir")),
    Skill("go", "Go", "engineering", _aliases("go", "golang")),
    Skill("godot", "Godot Engine", "engineering", _aliases("godot", "godot engine")),
    Skill("java", "Java", "engineering", _aliases("java", "jvm")),
    Skill("javascript", "JavaScript", "engineering", _aliases("javascript", "js")),
    Skill(
        "typescript",
        "TypeScript",
        "engineering",
        _aliases("typescript", "ts-node", "tsconfig"),
    ),
    # JavaScript frameworks/platforms from Sentry JS platforms
    Skill("react", "React", "engineering", _aliases("react", "reactjs", "react.js")),
    Skill("nextjs", "Next.js", "engineering", _aliases("next.js", "nextjs", "next js")),
    Skill("nodejs", "Node.js", "engineering", _aliases("node.js", "nodejs", "node")),
    Skill(
        "express",
        "Express",
        "engineering",
        _aliases("express", "express.js", "expressjs"),
    ),
    Skill("angular", "Angular", "engineering", _aliases("angular")),
    Skill("vue", "Vue", "engineering", _aliases("vue", "vue.js", "vuejs")),
    Skill("svelte", "Svelte", "engineering", _aliases("svelte")),
    Skill("remix", "Remix", "engineering", _aliases("remix", "remix.run")),
    Skill("nuxt", "Nuxt", "engineering", _aliases("nuxt", "nuxt.js", "nuxtjs")),
    Skill("gatsby", "Gatsby", "engineering", _aliases("gatsby", "gatsbyjs")),
    Skill("astro", "Astro", "engineering", _aliases("astro", "astro.build")),
    Skill("preact", "Preact", "engineering", _aliases("preact")),
    Skill("solid", "SolidJS", "engineering", _aliases("solid", "solidjs", "solid.js")),
    Skill("ember", "Ember", "engineering", _aliases("ember", "ember.js", "emberjs")),
    Skill(
        "electron",
        "Electron",
        "engineering",
        _aliases("electron", "electronjs", "electron.js"),
    ),
    Skill("deno", "Deno", "engineering", _aliases("deno")),
    Skill("bun", "Bun", "engineering", _aliases("bun", "bun.sh")),
    Skill(
        "cloudflare_workers",
        "Cloudflare Workers",
        "engineering",
        _aliases("cloudflare workers"),
    ),
    Skill("cloudflare", "Cloudflare", "engineering", _aliases("cloudflare")),
    Skill(
        "aws_lambda",
        "AWS Lambda",
        "engineering",
        _aliases("aws-lambda", "aws lambda", "lambda"),
    ),
    Skill(
        "gcp_functions",
        "GCP Cloud Functions",
        "engineering",
        _aliases("gcp-functions", "gcp functions", "cloud functions"),
    ),
    Skill(
        "azure_functions",
        "Azure Functions",
        "engineering",
        _aliases("azure-functions", "azure functions"),
    ),
    Skill("fastify", "Fastify", "engineering", _aliases("fastify")),
    Skill("hapi", "hapi", "engineering", _aliases("hapi", "@hapi")),
    Skill("hono", "Hono", "engineering", _aliases("hono")),
    Skill("koa", "Koa", "engineering", _aliases("koa")),
    Skill("nestjs", "NestJS", "engineering", _aliases("nestjs", "nest.js", "nest")),
    Skill("connect", "Connect (Node)", "engineering", _aliases("connect")),
    Skill(
        "react_router",
        "React Router",
        "engineering",
        _aliases("react-router", "react router"),
    ),
    Skill(
        "solidstart", "SolidStart", "engineering", _aliases("solidstart", "solid start")
    ),
    Skill("sveltekit", "SvelteKit", "engineering", _aliases("sveltekit")),
    Skill(
        "tanstackstart_react",
        "TanStack Start (React)",
        "engineering",
        _aliases("tanstackstart-react", "tanstack start react", "tanstack start"),
    ),
    Skill(
        "wasm",
        "WebAssembly",
        "engineering",
        _aliases("wasm", "webassembly", "web assembly"),
    ),
    Skill("ionic", "Ionic", "engineering", _aliases("ionic")),
    Skill("capacitor", "Capacitor", "engineering", _aliases("capacitor", "@capacitor")),
    Skill(
        "cordova",
        "Cordova",
        "engineering",
        _aliases("cordova", "apache cordova", "phonegap"),
    ),
    Skill(
        "service_workers",
        "Service Workers",
        "engineering",
        _aliases("service worker", "service workers"),
    ),
    Skill(
        "web_extensions",
        "Web Extensions",
        "engineering",
        _aliases(
            "web extension",
            "web extensions",
            "webextension",
            "webextensions",
            "browser extension",
        ),
    ),
    Skill("vite", "Vite", "engineering", _aliases("vite", "vitejs", "vite.js")),
    Skill("kotlin", "Kotlin", "engineering", _aliases("kotlin")),
    Skill(
        "native",
        "Native (C/C++)",
        "engineering",
        _aliases("native", "c", "c++", "c/c++"),
    ),
    Skill("dotnet", ".NET", "engineering", _aliases(".net", "dotnet", "c#", "asp.net")),
    Skill(
        "nintendo_switch",
        "Nintendo Switch",
        "engineering",
        _aliases("nintendo switch", "switch"),
    ),
    Skill("php", "PHP", "engineering", _aliases("php", "laravel", "symfony")),
    Skill(
        "playstation",
        "PlayStation",
        "engineering",
        _aliases("playstation", "ps4", "ps5"),
    ),
    Skill(
        "powershell", "PowerShell", "engineering", _aliases("powershell", "ps", "ps1")
    ),
    Skill(
        "python",
        "Python",
        "engineering",
        _aliases("python", "django", "flask", "fastapi"),
    ),
    # Python frameworks and libraries (from Sentry Python Integrations)
    # Web Frameworks
    Skill("django", "Django", "engineering", _aliases("django")),
    Skill("flask", "Flask", "engineering", _aliases("flask")),
    Skill("fastapi", "FastAPI", "engineering", _aliases("fastapi")),
    Skill("aiohttp", "AIOHTTP", "engineering", _aliases("aiohttp")),
    Skill("bottle", "Bottle", "engineering", _aliases("bottle")),
    Skill("falcon", "Falcon", "engineering", _aliases("falcon")),
    Skill("pyramid", "Pyramid", "engineering", _aliases("pyramid")),
    Skill("quart", "Quart", "engineering", _aliases("quart")),
    Skill("sanic", "Sanic", "engineering", _aliases("sanic")),
    Skill("starlette", "Starlette", "engineering", _aliases("starlette")),
    Skill("starlite", "Starlite", "engineering", _aliases("starlite")),
    Skill("litestar", "Litestar", "engineering", _aliases("litestar")),
    Skill("tornado", "Tornado", "engineering", _aliases("tornado")),
    # Databases
    Skill("asyncpg", "asyncpg", "engineering", _aliases("asyncpg")),
    Skill(
        "clickhouse_driver",
        "clickhouse-driver",
        "engineering",
        _aliases("clickhouse-driver", "clickhouse"),
    ),
    Skill("pymongo", "PyMongo", "engineering", _aliases("pymongo", "mongo", "mongodb")),
    Skill("redis", "Redis", "engineering", _aliases("redis")),
    Skill("sqlalchemy", "SQLAlchemy", "engineering", _aliases("sqlalchemy")),
    # AI
    Skill("anthropic", "Anthropic", "engineering", _aliases("anthropic")),
    Skill("openai", "OpenAI", "engineering", _aliases("openai")),
    Skill(
        "openai_agents",
        "OpenAI Agents SDK",
        "engineering",
        _aliases("openai agents", "openai-agents"),
    ),
    Skill("langchain", "LangChain", "engineering", _aliases("langchain")),
    # Data Processing
    Skill(
        "airflow",
        "Apache Airflow",
        "engineering",
        _aliases("airflow", "apache airflow"),
    ),
    Skill("beam", "Apache Beam", "engineering", _aliases("beam", "apache beam")),
    Skill("spark", "Apache Spark", "engineering", _aliases("spark", "apache spark")),
    Skill("arq", "ARQ", "engineering", _aliases("arq")),
    Skill("celery", "Celery", "engineering", _aliases("celery")),
    Skill("dramatiq", "Dramatiq", "engineering", _aliases("dramatiq")),
    Skill("huey", "Huey", "engineering", _aliases("huey")),
    Skill("rq", "RQ", "engineering", _aliases("rq", "redis queue")),
    Skill("ray", "Ray", "engineering", _aliases("ray")),
    # Feature Flags
    Skill("launchdarkly", "LaunchDarkly", "engineering", _aliases("launchdarkly")),
    Skill("openfeature", "OpenFeature", "engineering", _aliases("openfeature")),
    Skill("statsig", "Statsig", "engineering", _aliases("statsig")),
    Skill("unleash", "Unleash", "engineering", _aliases("unleash")),
    # Cloud Computing (Python-specific)
    Skill("boto3", "Boto3", "engineering", _aliases("boto3")),
    Skill("chalice", "Chalice", "engineering", _aliases("chalice", "aws chalice")),
    Skill(
        "cloud_resource_context",
        "Cloud Resource Context",
        "engineering",
        _aliases("cloud resource context"),
    ),
    Skill(
        "serverless_framework",
        "Serverless Framework",
        "engineering",
        _aliases("serverless", "serverless framework"),
    ),
    # HTTP Clients
    Skill("httpx", "HTTPX", "engineering", _aliases("httpx")),
    Skill("requests", "Requests", "engineering", _aliases("requests")),
    # GraphQL
    Skill("ariadne", "Ariadne", "engineering", _aliases("ariadne")),
    Skill("gql", "GQL", "engineering", _aliases("gql")),
    Skill("graphene", "Graphene", "engineering", _aliases("graphene")),
    Skill("strawberry", "Strawberry", "engineering", _aliases("strawberry")),
    # RPC
    Skill("grpc", "gRPC", "engineering", _aliases("grpc", "gRPC")),
    # Logging
    Skill(
        "logging",
        "Python Logging",
        "engineering",
        _aliases("logging", "python logging"),
    ),
    Skill("loguru", "Loguru", "engineering", _aliases("loguru")),
    # Miscellaneous
    Skill("asgi", "ASGI", "engineering", _aliases("asgi")),
    Skill("asyncio", "asyncio", "engineering", _aliases("asyncio")),
    Skill("pure_eval", "pure_eval", "engineering", _aliases("pure_eval", "pure eval")),
    Skill("gnu_backtrace", "GNU Backtrace", "engineering", _aliases("gnu backtrace")),
    Skill("rust_tracing", "Rust Tracing", "engineering", _aliases("rust tracing")),
    Skill("socket", "Socket", "engineering", _aliases("socket")),
    Skill("sys_exit", "sys.exit", "engineering", _aliases("sys.exit", "sys exit")),
    Skill("tryton", "Tryton", "engineering", _aliases("tryton")),
    Skill("typer", "Typer", "engineering", _aliases("typer")),
    Skill("wsgi", "WSGI", "engineering", _aliases("wsgi")),
    Skill(
        "react_native", "React Native", "engineering", _aliases("react native", "rn")
    ),
    Skill("ruby", "Ruby", "engineering", _aliases("ruby", "rails", "ruby on rails")),
    Skill("rust", "Rust", "engineering", _aliases("rust")),
    Skill("unity", "Unity", "engineering", _aliases("unity", "unity3d", "unity 3d")),
    Skill(
        "unreal",
        "Unreal Engine",
        "engineering",
        _aliases("unreal", "unreal engine", "ue", "ue4", "ue5"),
    ),
    Skill("xbox", "Xbox", "engineering", _aliases("xbox")),
]


# SaaS business topics (seed)
BUSINESS_SKILLS: list[Skill] = [
    # Marketing
    Skill("seo", "SEO", "marketing", _aliases("seo", "search engine optimization")),
    Skill(
        "sem",
        "SEM / Paid Search",
        "marketing",
        _aliases("sem", "paid search", "google ads", "adwords"),
    ),
    Skill(
        "content_marketing",
        "Content Marketing",
        "marketing",
        _aliases("content marketing", "copywriting", "editorial"),
    ),
    Skill(
        "email_marketing",
        "Email Marketing",
        "marketing",
        _aliases("email marketing", "mailchimp", "marketo", "hubspot email"),
    ),
    Skill(
        "marketing_automation",
        "Marketing Automation",
        "marketing",
        _aliases("marketing automation", "hubspot", "marketo", "pardot"),
    ),
    Skill(
        "product_marketing",
        "Product Marketing",
        "marketing",
        _aliases("product marketing", "pmM"),
    ),
    Skill(
        "growth",
        "Growth Marketing",
        "marketing",
        _aliases("growth", "growth marketing", "growth loops"),
    ),
    Skill(
        "social_media",
        "Social Media",
        "marketing",
        _aliases("social media", "linkedin", "twitter", "x"),
    ),
    Skill(
        "analytics_ga",
        "Web Analytics (GA4)",
        "marketing",
        _aliases("ga4", "google analytics", "web analytics"),
    ),
    Skill(
        "ab_testing",
        "A/B Testing / Experimentation",
        "marketing",
        _aliases("a/b testing", "ab testing", "experimentation", "optimizely"),
    ),
    Skill(
        "cro",
        "Conversion Rate Optimization",
        "marketing",
        _aliases("cro", "conversion rate optimization"),
    ),
    # Sales
    Skill("salesforce", "Salesforce", "sales", _aliases("salesforce", "sfdc")),
    Skill("hubspot_crm", "HubSpot CRM", "sales", _aliases("hubspot crm", "hubspot")),
    Skill(
        "prospecting",
        "Prospecting / Outbound",
        "sales",
        _aliases("prospecting", "outbound", "cold outreach"),
    ),
    Skill("inbound_sales", "Inbound Sales", "sales", _aliases("inbound sales")),
    Skill("negotiation", "Negotiation", "sales", _aliases("negotiation")),
    Skill(
        "forecasting",
        "Forecasting & Pipeline",
        "sales",
        _aliases("forecasting", "pipeline"),
    ),
    Skill(
        "meddic",
        "MEDDIC / Qualification",
        "sales",
        _aliases("meddic", "bant", "qualification"),
    ),
    Skill("pricing", "Pricing & Packaging", "sales", _aliases("pricing", "packaging")),
    Skill(
        "renewals",
        "Renewals / Expansion",
        "sales",
        _aliases("renewals", "expansion", "upsell", "cross-sell"),
    ),
    # Product
    Skill(
        "product_management",
        "Product Management",
        "product",
        _aliases("product management", "pm"),
    ),
    Skill("roadmapping", "Roadmapping", "product", _aliases("roadmap", "roadmapping")),
    Skill(
        "prioritization",
        "Prioritization",
        "product",
        _aliases("prioritization", "rICE", "wsjf"),
    ),
    Skill(
        "user_research",
        "User Research",
        "product",
        _aliases("user research", "interviews", "usability testing"),
    ),
    Skill("okrs", "OKRs", "product", _aliases("okrs")),
    Skill(
        "plg", "Product-Led Growth", "product", _aliases("plg", "product led growth")
    ),
    # Design
    Skill("ux", "UX", "design", _aliases("ux", "user experience")),
    Skill("ui", "UI", "design", _aliases("ui", "user interface")),
    Skill("product_design", "Product Design", "design", _aliases("product design")),
    Skill(
        "design_systems",
        "Design Systems",
        "design",
        _aliases("design system", "design systems"),
    ),
    Skill("figma", "Figma", "design", _aliases("figma")),
    Skill(
        "accessibility",
        "Accessibility (a11y)",
        "design",
        _aliases("accessibility", "a11y"),
    ),
    # Data
    Skill("sql", "SQL", "data", _aliases("sql")),
    Skill("dbt", "dbt", "data", _aliases("dbt")),
    Skill("snowflake", "Snowflake", "data", _aliases("snowflake")),
    Skill("bigquery", "BigQuery", "data", _aliases("bigquery", "bq")),
    Skill("etl", "ETL / ELT", "data", _aliases("etl", "elt", "data pipeline")),
    Skill(
        "bi",
        "Business Intelligence",
        "data",
        _aliases("bi", "looker", "tableau", "powerbi", "power bi"),
    ),
    Skill(
        "experimentation",
        "Experimentation / Stats",
        "data",
        _aliases("experimentation", "statistical testing", "bayesian", "frequentist"),
    ),
    # DevOps / SRE
    Skill(
        "aws",
        "AWS",
        "devops",
        _aliases("aws", "amazon web services", "ec2", "s3", "lambda"),
    ),
    Skill("gcp", "GCP", "devops", _aliases("gcp", "google cloud", "gke", "bigquery")),
    Skill("azure", "Azure", "devops", _aliases("azure")),
    Skill("kubernetes", "Kubernetes", "devops", _aliases("kubernetes", "k8s")),
    Skill("docker", "Docker", "devops", _aliases("docker")),
    Skill("terraform", "Terraform", "devops", _aliases("terraform")),
    Skill(
        "cicd",
        "CI/CD",
        "devops",
        _aliases("ci/cd", "ci cd", "continuous integration", "continuous delivery"),
    ),
    Skill(
        "observability",
        "Observability",
        "devops",
        _aliases("observability", "prometheus", "grafana", "sentry"),
    ),
    # Customer Success / Support
    Skill(
        "onboarding", "Customer Onboarding", "customer_success", _aliases("onboarding")
    ),
    Skill(
        "retention",
        "Retention / NRR",
        "customer_success",
        _aliases("retention", "nrr", "churn"),
    ),
    Skill(
        "support",
        "Customer Support / SLAs",
        "customer_success",
        _aliases("support", "sla", "ticketing", "zendesk", "intercom"),
    ),
]


SENTRY_PRODUCT_SKILLS: list[Skill] = [
    # ai-in-sentry
    Skill("ai_in_sentry", "AI in Sentry", "sentry", _aliases("ai-in-sentry")),
    Skill(
        "ai_privacy_and_security",
        "AI Privacy and Security",
        "sentry",
        _aliases("ai-privacy-and-security", "ai privacy", "ai security"),
    ),
    Skill("seer", "Seer", "sentry", _aliases("seer")),
    Skill(
        "sentry_prevent_ai",
        "Sentry Prevent AI",
        "sentry",
        _aliases("sentry-prevent-ai"),
    ),
    # alerts
    Skill("alerts", "Alerts", "sentry", _aliases("alerts")),
    Skill("create_alerts", "Create Alerts", "sentry", _aliases("create-alerts")),
    Skill("notifications", "Notifications", "sentry", _aliases("notifications")),
    # codecov
    Skill("codecov", "Codecov", "sentry", _aliases("codecov")),
    # crons
    Skill("crons", "Crons", "sentry", _aliases("crons")),
    # dashboards
    Skill("dashboards", "Dashboards", "sentry", _aliases("dashboards")),
    Skill(
        "custom_dashboards",
        "Custom Dashboards",
        "sentry",
        _aliases("custom-dashboards"),
    ),
    Skill("widget_builder", "Widget Builder", "sentry", _aliases("widget-builder")),
    Skill("widget_library", "Widget Library", "sentry", _aliases("widget-library")),
    # explore
    Skill("explore", "Explore", "sentry", _aliases("explore")),
    Skill(
        "discover_queries", "Discover Queries", "sentry", _aliases("discover-queries")
    ),
    Skill("logs", "Logs", "sentry", _aliases("logs")),
    Skill("profiling", "Profiling", "sentry", _aliases("profiling")),
    Skill("session_replay", "Session Replay", "sentry", _aliases("session-replay")),
    Skill("trace_explorer", "Trace Explorer", "sentry", _aliases("trace-explorer")),
    # insights
    Skill("insights", "Insights", "sentry", _aliases("insights")),
    Skill("insights_ai", "Insights - AI", "sentry", _aliases("insights ai")),
    Skill(
        "insights_backend", "Insights - Backend", "sentry", _aliases("insights backend")
    ),
    Skill(
        "insights_frontend",
        "Insights - Frontend",
        "sentry",
        _aliases("insights frontend"),
    ),
    Skill(
        "insights_mobile", "Insights - Mobile", "sentry", _aliases("insights mobile")
    ),
    Skill(
        "insights_overview",
        "Insights - Overview",
        "sentry",
        _aliases("insights overview"),
    ),
    Skill(
        "insights_getting_started",
        "Insights - Getting Started",
        "sentry",
        _aliases("getting-started.mdx", "insights getting started"),
    ),
    Skill(
        "performance_overhead",
        "Performance Overhead",
        "sentry",
        _aliases("performance-overhead.mdx", "performance overhead"),
    ),
    # issues
    Skill("issues", "Issues", "sentry", _aliases("issues")),
    Skill(
        "grouping_and_fingerprints",
        "Grouping and Fingerprints",
        "sentry",
        _aliases("grouping-and-fingerprints"),
    ),
    Skill("issue_details", "Issue Details", "sentry", _aliases("issue-details")),
    Skill("issue_priority", "Issue Priority", "sentry", _aliases("issue-priority")),
    Skill("issue_views", "Issue Views", "sentry", _aliases("issue-views")),
    Skill("ownership_rules", "Ownership Rules", "sentry", _aliases("ownership-rules")),
    Skill("reprocessing", "Reprocessing", "sentry", _aliases("reprocessing")),
    Skill("states_triage", "States & Triage", "sentry", _aliases("states-triage")),
    Skill("suspect_commits", "Suspect Commits", "sentry", _aliases("suspect-commits")),
    # onboarding
    Skill("onboarding_sentry", "Onboarding (Sentry)", "sentry", _aliases("onboarding")),
    # partnership-platform
    Skill(
        "partnership_platform",
        "Partnership Platform",
        "sentry",
        _aliases("partnership-platform"),
    ),
    Skill(
        "account_provisioning_api",
        "Account Provisioning API",
        "sentry",
        _aliases("account-provisioning-api"),
    ),
    # projects
    Skill("projects", "Projects", "sentry", _aliases("projects")),
    Skill("project_details", "Project Details", "sentry", _aliases("project-details")),
    # relay
    Skill("relay", "Relay", "sentry", _aliases("relay")),
    # releases
    Skill("releases", "Releases", "sentry", _aliases("releases")),
    Skill(
        "associate_commits",
        "Associate Commits",
        "sentry",
        _aliases("associate-commits"),
    ),
    Skill(
        "release_health",
        "Release Health",
        "sentry",
        _aliases("health", "release health"),
    ),
    # sentry-basics
    Skill("sentry_basics", "Sentry Basics", "sentry", _aliases("sentry-basics")),
    Skill(
        "distributed_tracing",
        "Distributed Tracing",
        "sentry",
        _aliases("distributed-tracing"),
    ),
    # sentry-mcp
    Skill("sentry_mcp", "Sentry MCP", "sentry", _aliases("sentry-mcp")),
    # sentry-toolbar
    Skill("sentry_toolbar", "Sentry Toolbar", "sentry", _aliases("sentry-toolbar")),
    # stats
    Skill("stats", "Stats", "sentry", _aliases("stats")),
    # uptime-monitoring
    Skill(
        "uptime_monitoring",
        "Uptime Monitoring",
        "sentry",
        _aliases("uptime-monitoring", "uptime monitoring"),
    ),
    # user-feedback
    Skill(
        "user_feedback",
        "User Feedback",
        "sentry",
        _aliases("user-feedback", "user feedback"),
    ),
    # security-legal-pii
    Skill(
        "security_legal_pii",
        "Security, Legal & PII",
        "sentry",
        _aliases("security-legal-pii"),
    ),
    Skill(
        "pii",
        "PII (Personal Identifiable Information)",
        "sentry",
        _aliases("pii", "personal identifiable information"),
    ),
    Skill("scrubbing", "Data Scrubbing", "sentry", _aliases("scrubbing")),
    Skill("security", "Security", "sentry", _aliases("security")),
]


SKILLS: list[Skill] = ENGINEERING_SDK_SKILLS + BUSINESS_SKILLS + SENTRY_PRODUCT_SKILLS


class SkillMatcher:
    """Very lightweight alias-based matcher.

    - Word-boundary, case-insensitive matching over text
    - Maps any alias to a canonical skill key
    """

    def __init__(self, skills: Iterable[Skill] | None = None) -> None:
        self.skills: list[Skill] = list(skills or SKILLS)
        self.alias_to_key: dict[str, str] = {}
        self.key_to_skill: dict[str, Skill] = {s.key: s for s in self.skills}
        for skill in self.skills:
            for alias in (skill.name.lower(),) + skill.aliases:
                self.alias_to_key[alias] = skill.key

        # Precompile regexes per alias
        # Use negative lookbehind/ahead to avoid partial matches inside words
        boundary = r"(?<![\w/#.])({})(?![\w-])"
        self.alias_regex: list[tuple[re.Pattern[str], str]] = []
        for alias, key in self.alias_to_key.items():
            # Escape regex special chars except for spaces which we convert to \s+
            escaped = re.escape(alias).replace("\\ ", r"\\s+")
            pattern = re.compile(boundary.format(escaped), re.IGNORECASE)
            self.alias_regex.append((pattern, key))

    def match_text(self, text: str) -> list[str]:
        if not text:
            return []
        matches: list[str] = []
        # Light normalization: collapse whitespace
        normalized = re.sub(r"\s+", " ", text)
        for pattern, key in self.alias_regex:
            if pattern.search(normalized):
                matches.append(key)
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique = []
        for k in matches:
            if k not in seen:
                unique.append(k)
                seen.add(k)
        return unique

    def describe(self, key: str) -> Skill | None:
        return self.key_to_skill.get(key)
