-- Indexes for the web app's read paths.
-- Without them, "latest pull" (ORDER BY scraped_at DESC LIMIT 1) seq-scanned
-- raw_listings and the listings loader re-sorted classified_listings on every
-- page; both started exceeding the anon role's 3s statement_timeout and took
-- the dashboard down. Already applied to production on 2026-10-10.

CREATE INDEX IF NOT EXISTS raw_listings_scraped_at_idx
    ON raw_listings (scraped_at DESC);

-- Keyset pagination in web/src/lib/data.ts orders by (classified_at, id).
CREATE INDEX IF NOT EXISTS classified_listings_classified_at_id_idx
    ON classified_listings (classified_at DESC, id DESC);

-- Superseded by the composite index above (created briefly during the fix).
DROP INDEX IF EXISTS classified_listings_classified_at_idx;
