-- GENIE OPS Database Schema
-- PostgreSQL Database Schema for SaaS Directory Submission Agent
-- Run this script in PostgreSQL Admin to create the database structure

-- Enable UUID extension if needed (optional)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create SAAS Products table
CREATE TABLE IF NOT EXISTS saas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    contact_email VARCHAR(255) NOT NULL,
    logo_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create Directories table
CREATE TABLE IF NOT EXISTS directories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create Submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id SERIAL PRIMARY KEY,
    saas_id INTEGER NOT NULL,
    directory_id INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'approved', 'failed')),
    submitted_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    form_data TEXT,  -- JSON string
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE,
    FOREIGN KEY (saas_id) REFERENCES saas(id) ON DELETE CASCADE,
    FOREIGN KEY (directory_id) REFERENCES directories(id) ON DELETE CASCADE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_saas_name ON saas(name);
CREATE INDEX IF NOT EXISTS idx_saas_url ON saas(url);
CREATE INDEX IF NOT EXISTS idx_directories_name ON directories(name);
CREATE INDEX IF NOT EXISTS idx_directories_url ON directories(url);
CREATE INDEX IF NOT EXISTS idx_submissions_saas_id ON submissions(saas_id);
CREATE INDEX IF NOT EXISTS idx_submissions_directory_id ON submissions(directory_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status ON submissions(status);
CREATE INDEX IF NOT EXISTS idx_submissions_created_at ON submissions(created_at);

-- Create a composite index for common queries
CREATE INDEX IF NOT EXISTS idx_submissions_saas_directory ON submissions(saas_id, directory_id);
CREATE INDEX IF NOT EXISTS idx_submissions_status_created ON submissions(status, created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_saas_updated_at BEFORE UPDATE ON saas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_submissions_updated_at BEFORE UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE saas IS 'Stores SaaS product information';
COMMENT ON TABLE directories IS 'Stores directory websites where submissions will be made';
COMMENT ON TABLE submissions IS 'Tracks submission status for each SaaS product in each directory';

COMMENT ON COLUMN submissions.status IS 'Status: pending, submitted, approved, or failed';
COMMENT ON COLUMN submissions.retry_count IS 'Number of retry attempts for failed submissions';
COMMENT ON COLUMN submissions.form_data IS 'JSON string containing form data used for submission';

-- Sample data (optional - uncomment to insert test data)
/*
-- Insert sample SaaS
INSERT INTO saas (name, url, description, category, contact_email, logo_path) VALUES
('Example SaaS', 'https://example.com', 'An example SaaS product', 'Productivity', 'contact@example.com', '/logos/example.png');

-- Insert sample directories
INSERT INTO directories (name, url, description) VALUES
('Directory 1', 'https://directory1.com/submit', 'First directory'),
('Directory 2', 'https://directory2.com/add-listing', 'Second directory');
*/
