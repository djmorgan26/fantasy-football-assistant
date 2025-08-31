-- Initialize database for Fantasy Football Assistant

-- Create database (this is handled by docker-compose)
-- CREATE DATABASE fantasy_football_db;

-- Create user (this is handled by docker-compose)  
-- CREATE USER fantasy_user WITH PASSWORD 'fantasy_password';

-- Grant privileges
-- GRANT ALL PRIVILEGES ON DATABASE fantasy_football_db TO fantasy_user;

-- Set up extensions if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- This file is mainly a placeholder for future initialization scripts
-- The actual database schema is created by Alembic migrations