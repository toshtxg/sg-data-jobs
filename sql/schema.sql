-- SG AI Job Market Scout — Database Schema
-- Run this in the Supabase Dashboard SQL Editor

CREATE TABLE IF NOT EXISTS raw_listings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source TEXT NOT NULL,
    source_url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    description TEXT,
    salary_min NUMERIC,
    salary_max NUMERIC,
    salary_currency TEXT DEFAULT 'SGD',
    posting_date DATE,
    expiry_date DATE,
    original_posting_date DATE,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    raw_data JSONB
);

CREATE TABLE IF NOT EXISTS classified_listings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    listing_id UUID NOT NULL UNIQUE REFERENCES raw_listings(id) ON DELETE CASCADE,
    role_category TEXT,
    seniority_level TEXT,
    technical_skills TEXT[],
    soft_skills TEXT[],
    domain_knowledge TEXT[],
    requires_ai_ml BOOLEAN,
    remote_hybrid_onsite TEXT,
    industry TEXT,
    classified_at TIMESTAMPTZ DEFAULT NOW(),
    model_used TEXT DEFAULT 'gpt-5-nano'
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_listings INTEGER,
    listings_by_role JSONB,
    listings_by_seniority JSONB,
    top_skills JSONB,
    avg_salary_by_role JSONB,
    new_listings_count INTEGER,
    salary_percentiles_by_role JSONB,
    active_listings_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Read-path indexes for the web app (latest pull + keyset pagination)
CREATE INDEX IF NOT EXISTS raw_listings_scraped_at_idx
    ON raw_listings (scraped_at DESC);
CREATE INDEX IF NOT EXISTS classified_listings_classified_at_id_idx
    ON classified_listings (classified_at DESC, id DESC);

-- Row-Level Security
-- Enable RLS on all tables (pipeline uses service_role key which bypasses RLS)
ALTER TABLE raw_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE classified_listings ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_snapshots ENABLE ROW LEVEL SECURITY;

-- Allow public read-only access for the website (anon key)
CREATE POLICY "Public read" ON raw_listings FOR SELECT TO anon USING (true);
CREATE POLICY "Public read" ON classified_listings FOR SELECT TO anon USING (true);
CREATE POLICY "Public read" ON market_snapshots FOR SELECT TO anon USING (true);
