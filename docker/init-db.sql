-- NOCTIS DICOM Viewer Database Initialization Script

-- Create database if not exists (run as superuser)
-- CREATE DATABASE noctis_db;

-- Create user if not exists (run as superuser)
-- CREATE USER noctis_user WITH PASSWORD 'your_password_here';

-- Grant privileges
-- GRANT ALL PRIVILEGES ON DATABASE noctis_db TO noctis_user;

-- Connect to the database
\c noctis_db;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE study_status AS ENUM ('pending', 'in_progress', 'completed', 'archived');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE priority_level AS ENUM ('routine', 'urgent', 'stat', 'asap');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create indexes for better performance
-- These will be created after Django migrations

-- Function to update modified timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Performance tuning settings (adjust based on your server specs)
-- These should be set in postgresql.conf, but included here for reference
-- ALTER SYSTEM SET shared_buffers = '2GB';
-- ALTER SYSTEM SET effective_cache_size = '6GB';
-- ALTER SYSTEM SET maintenance_work_mem = '512MB';
-- ALTER SYSTEM SET checkpoint_completion_target = 0.9;
-- ALTER SYSTEM SET wal_buffers = '16MB';
-- ALTER SYSTEM SET default_statistics_target = 100;
-- ALTER SYSTEM SET random_page_cost = 1.1;
-- ALTER SYSTEM SET effective_io_concurrency = 200;
-- ALTER SYSTEM SET work_mem = '16MB';
-- ALTER SYSTEM SET min_wal_size = '1GB';
-- ALTER SYSTEM SET max_wal_size = '4GB';

-- Create tablespaces for better data organization (optional)
-- CREATE TABLESPACE dicom_data LOCATION '/var/lib/postgresql/tablespaces/dicom_data';
-- CREATE TABLESPACE dicom_indexes LOCATION '/var/lib/postgresql/tablespaces/dicom_indexes';

GRANT USAGE ON SCHEMA public TO noctis_user;
GRANT CREATE ON SCHEMA public TO noctis_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO noctis_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO noctis_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO noctis_user;