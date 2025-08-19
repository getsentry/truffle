-- Truffle Expertise System Database Schema
-- PostgreSQL + pgvector for structured data and vector search

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users (integer ID with Slack ID for @mentions)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,           -- Internal integer ID
    slack_id TEXT NOT NULL UNIQUE,        -- Slack user ID (e.g., "U1234567890") for @mentions
    display_name TEXT NOT NULL,           -- For UI display
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skills with embeddings for semantic search
CREATE TABLE skills (
    skill_id SERIAL PRIMARY KEY,          -- Internal integer ID
    skill_key TEXT NOT NULL UNIQUE,       -- e.g., "react", "dynamic_sampling"
    name TEXT NOT NULL,                   -- e.g., "React", "Dynamic Sampling"
    domain TEXT NOT NULL,                 -- e.g., "engineering", "sentry"
    embedding vector(1536),               -- For "who knows dynamic sampling" queries
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Expertise evidence (no message content!)
CREATE TABLE expertise_evidence (
    evidence_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    label TEXT NOT NULL,                  -- positive_expertise|negative_expertise|neutral
    confidence REAL NOT NULL,
    evidence_date DATE NOT NULL,          -- Just the date, not full timestamp
    message_hash TEXT,                    -- Optional: for deduplication only
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- Pre-computed user expertise scores
CREATE TABLE user_skill_scores (
    user_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    score REAL NOT NULL,
    evidence_count INTEGER NOT NULL,
    last_evidence_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id)
);

-- Indexes for fast querying
CREATE INDEX idx_expertise_user_skill ON expertise_evidence(user_id, skill_id);
CREATE INDEX idx_expertise_date ON expertise_evidence(evidence_date);
CREATE INDEX idx_user_scores_skill ON user_skill_scores(skill_id, score DESC);
CREATE INDEX idx_skills_embedding ON skills USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_users_slack_id ON users(slack_id);
CREATE INDEX idx_skills_key ON skills(skill_key);

-- Trigger to auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_expertise_evidence_updated_at BEFORE UPDATE ON expertise_evidence
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_skill_scores_updated_at BEFORE UPDATE ON user_skill_scores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
