-- Migration: 002_create_network_connections_table.sql
-- Create network connections table

CREATE TABLE IF NOT EXISTS network_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    company VARCHAR(255),
    position VARCHAR(255),
    relationship VARCHAR(100) CHECK (relationship IN ('close', 'moderate', 'distant', 'unknown')),
    skills JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    linkedin_url TEXT,
    github_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_network_connections_name ON network_connections(name);
CREATE INDEX IF NOT EXISTS idx_network_connections_company ON network_connections(company);
CREATE INDEX IF NOT EXISTS idx_network_connections_relationship ON network_connections(relationship);
CREATE INDEX IF NOT EXISTS idx_network_connections_skills ON network_connections USING GIN(skills);
CREATE UNIQUE INDEX IF NOT EXISTS idx_network_connections_email ON network_connections(email) WHERE email IS NOT NULL;

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS update_network_connections_updated_at ON network_connections;
CREATE TRIGGER update_network_connections_updated_at 
    BEFORE UPDATE ON network_connections 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
