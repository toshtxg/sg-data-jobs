#!/usr/bin/env python3
"""
Run the full scraping -> classification -> snapshot pipeline.
Usage: python pipeline/run_pipeline.py
"""
import logging
import os
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

from pipeline.classifier import ClassificationPipelineError, classify_unprocessed
from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper
from pipeline.snapshot import generate_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Classification stops starting new batches this many minutes after the
# pipeline starts, leaving headroom under the workflow's 45-minute timeout for
# in-flight batches and the snapshot. Unclassified listings carry over to the
# next run.
CLASSIFY_DEADLINE_MINUTES = float(
    (os.environ.get("CLASSIFY_DEADLINE_MINUTES") or "35").strip()
)

SEARCH_TERMS = [
    # Data Science
    "data scientist",
    "data science",
    "data analyst",
    "data engineer",
    "data architect",
    "data manager",
    # AI / ML
    "machine learning engineer",
    "AI engineer",
    "artificial intelligence",
    "deep learning",
    "computer vision",
    "MLOps",
    "NLP",
    "LLM",
    "generative AI",
    "prompt engineer",
    # Analytics / BI
    "analytics",
    "analytics engineer",
    "business intelligence",
    "BI analyst",
    "BI developer",
    "business analyst data",
    "reporting analyst",
    "insights analyst",
    # Research
    "research scientist AI",
    "applied scientist",
    "quantitative analyst",
]


def _get_existing_urls(client) -> set[str]:
    """Fetch all source_urls already in raw_listings."""
    existing = set()
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("raw_listings")
            .select("source_url")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        for row in resp.data:
            existing.add(row["source_url"])
        if len(resp.data) < page_size:
            break
        offset += page_size
    return existing


# Lifecycle columns added by sql/migrations/2026-07-05-listing-lifecycle.sql.
# Stripped from upsert payloads on the fallback path when the migration is
# not yet applied.
LIFECYCLE_KEYS = ("expiry_date", "original_posting_date", "last_seen_at")
_warned_lifecycle_upsert = False


def _upsert_raw_listings(client, rows: list[dict]) -> int:
    """Upsert rows into raw_listings on source_url.

    If the lifecycle columns are missing (migration not yet run), warn once
    naming the migration file and retry with those keys stripped.
    """
    global _warned_lifecycle_upsert
    try:
        response = (
            client.table("raw_listings")
            .upsert(rows, on_conflict="source_url")
            .execute()
        )
        return len(response.data)
    except Exception as first_error:
        if not _warned_lifecycle_upsert:
            logger.warning(
                "raw_listings upsert failed (likely missing lifecycle columns). "
                "Run sql/migrations/2026-07-05-listing-lifecycle.sql in Supabase, "
                "then retry. Falling back without lifecycle fields for now: %s",
                first_error,
            )
            _warned_lifecycle_upsert = True
        stripped = [
            {k: v for k, v in row.items() if k not in LIFECYCLE_KEYS}
            for row in rows
        ]
        try:
            response = (
                client.table("raw_listings")
                .upsert(stripped, on_conflict="source_url")
                .execute()
            )
            return len(response.data)
        except Exception as second_error:
            logger.error(
                "raw_listings upsert failed after fallback: %s", second_error
            )
            return 0


def store_listings(
    listings: list[dict], client, existing_urls: set[str]
) -> tuple[int, int]:
    """Insert new listings and refresh lifecycle fields on already-known ones.

    Returns (inserted, refreshed).
    """
    if not listings:
        return 0, 0

    new_listings = [l for l in listings if l["source_url"] not in existing_urls]
    known_listings = [l for l in listings if l["source_url"] in existing_urls]

    batch_size = 100

    # Insert truly new listings with their full payload.
    inserted = 0
    for i in range(0, len(new_listings), batch_size):
        batch = new_listings[i : i + batch_size]
        inserted += _upsert_raw_listings(client, batch)

    # Refresh already-known listings with a slim lifecycle payload so
    # reposted/renewed listings stay fresh. source and title are included to
    # satisfy NOT NULL constraints on the upsert's insert path.
    now = datetime.now(timezone.utc).isoformat()
    refresh_payload = [
        {
            "source_url": l["source_url"],
            "source": l["source"],
            "title": l["title"],
            "last_seen_at": now,
            "expiry_date": l.get("expiry_date"),
            "original_posting_date": l.get("original_posting_date"),
            "posting_date": l.get("posting_date"),
            "salary_min": l.get("salary_min"),
            "salary_max": l.get("salary_max"),
        }
        for l in known_listings
    ]
    refreshed = 0
    for i in range(0, len(refresh_payload), batch_size):
        batch = refresh_payload[i : i + batch_size]
        refreshed += _upsert_raw_listings(client, batch)

    logger.info(
        f"Inserted {inserted} new listings, refreshed {refreshed} existing"
    )
    return inserted, refreshed


def main():
    started_at = time.monotonic()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        logger.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        sys.exit(1)

    client = create_client(url, key)
    logger.info("=" * 60)
    logger.info("SG AI Job Market Scout — Pipeline Run")
    logger.info("=" * 60)

    # --- Phase A: Scrape ---
    logger.info("--- PHASE A: Scraping ---")
    # Fetch the existing-URL set once and reuse it for scraper early-stop and
    # for splitting scraped listings into new vs already-known.
    known_urls = _get_existing_urls(client)
    logger.info(f"Known listings in database: {len(known_urls)}")
    scrapers = [
        MyCareersFutureScraper(),
    ]
    total_inserted = 0
    total_refreshed = 0
    for scraper in scrapers:
        try:
            listings = scraper.scrape_all(
                SEARCH_TERMS, max_pages=5, known_urls=known_urls
            )
            if listings:
                inserted, refreshed = store_listings(listings, client, known_urls)
                total_inserted += inserted
                total_refreshed += refreshed
                logger.info(
                    f"[{scraper.source_name}] Inserted {inserted}, "
                    f"refreshed {refreshed}"
                )
            else:
                logger.info(f"[{scraper.source_name}] No listings found")
        except Exception as e:
            logger.error(f"[{scraper.source_name}] Scraper failed: {e}")

    logger.info(
        f"Total inserted: {total_inserted}, total refreshed: {total_refreshed}"
    )

    # --- Phase B: Classify ---
    logger.info("--- PHASE B: Classification ---")
    try:
        classified_count = classify_unprocessed(
            client, deadline=started_at + CLASSIFY_DEADLINE_MINUTES * 60
        )
        logger.info(f"Classified {classified_count} new listings")
    except ClassificationPipelineError as e:
        logger.error(f"Classification failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        sys.exit(1)

    # --- Phase C: Snapshot ---
    logger.info("--- PHASE C: Snapshot ---")
    try:
        snapshot = generate_snapshot(client)
        logger.info(
            f"Snapshot: {snapshot.get('total_listings', 0)} total listings, "
            f"{snapshot.get('new_listings_count', 0)} new this week"
        )
    except Exception as e:
        logger.error(f"Snapshot generation failed: {e}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Pipeline complete")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
