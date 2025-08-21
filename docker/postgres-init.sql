-- PostgreSQL initialization script for Truffle
-- This script runs automatically when postgres container starts for the first time

-- Ensure the truffle user has proper password authentication
ALTER USER truffle PASSWORD 'truffle';

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE truffle TO truffle;
