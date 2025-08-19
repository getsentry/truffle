
-- $ sudo -u postgres psql

-- Create the truffle user with password
CREATE USER truffle WITH PASSWORD 'your_secure_password_here';

-- Create the truffle database owned by the truffle user
CREATE DATABASE truffle OWNER truffle;

-- Grant all privileges on the database to the truffle user
GRANT ALL PRIVILEGES ON DATABASE truffle TO truffle;

\q

-- Test database connection
-- Test that the truffle user can connect to the truffle database
-- $ psql -h localhost -U truffle -d truffle
