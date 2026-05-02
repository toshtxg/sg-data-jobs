# SG Data & AI Job Pulse

A live look at Singapore's data, analytics, and AI job listings. Listings are sourced from [MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/), classified with GPT-5-nano, and surfaced through two front-ends.

**Two front-ends:**
- **Streamlit** (`app/`) — quick dashboard, deployed to [sg-ai-job-scout.streamlit.app](https://sg-ai-job-scout.streamlit.app/)
- **Next.js** (`web/`, package `sg-data-ai-job-pulse`) — production dashboard, deployed to Vercel

> **About the data.** MyCareersFuture is Singapore's government-mandated job portal. Under the [Fair Consideration Framework](https://www.mom.gov.sg/employment-practices/fair-consideration-framework), employers must post on MCF for at least 14 days before applying for an Employment Pass or S Pass. This dataset is therefore a **slice** of the SG market — skewed toward roles where employers are open to hiring foreign talent — not a complete picture.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![License](https://img.shields.io/badge/License-MIT-green)

## Architecture

```
sg-ai-job-scout/
├── app/                          # Streamlit frontend (focused, share-friendly)
│   ├── Home.py                   # Landing + caveat + nav
│   ├── pages/
│   │   ├── 1_Dashboard.py        # Headline metrics, role mix, salary distribution, new listings
│   │   └── 2_Job_Explorer.py     # Filterable job browser with apply links
│   ├── pages_hidden/             # Older deep-dives (kept alive, hidden from nav)
│   │   ├── 3_Role_Taxonomy.py
│   │   ├── 5_Company_Leaderboard.py
│   │   ├── 6_Jobs_For_You.py
│   │   ├── 7_Skills_Gap.py
│   │   ├── 8_AI_Skills_Deep_Dive.py
│   │   ├── 9_Skills_Salary_Premium.py
│   │   ├── 10_Learning_Roadmap.py
│   │   └── 11_Market_Pulse.py
│   ├── components/               # Reusable UI (charts, filters, metrics)
│   └── utils/                    # Config & Supabase client
├── web/                          # Next.js 16 frontend (Vercel)
│   ├── src/app/                  # App-router routes (Dashboard + Job Explorer in nav)
│   ├── src/components/           # React UI (charts, salary-distribution, data-caveat)
│   └── src/lib/                  # Supabase loader, salary helpers, taxonomy constants
├── pipeline/                     # Data pipeline (shared by both front-ends)
│   ├── scrapers/
│   │   └── mycareersfuture.py    # MCF API scraper
│   ├── classifier.py             # GPT-5-nano structured classification
│   ├── ai_skills_analyzer.py     # 281-keyword AI skills taxonomy
│   ├── skills_normalizer.py      # Canonical skill name mapping
│   ├── snapshot.py               # Market snapshot aggregation
│   └── run_pipeline.py           # Pipeline orchestrator (27 search terms)
├── sql/schema.sql                # Database DDL (run in Supabase)
├── .github/workflows/scrape.yml  # Automated scraping (daily at 2am UTC)
├── pyproject.toml
├── requirements.txt
└── .env.example
```

**Data flow:** MyCareersFuture API → Supabase (`raw_listings`) → GPT-5-nano classifier → Supabase (`classified_listings`) → Snapshot aggregation → Streamlit + Next.js dashboards

## Pages (visible in both front-ends)

| Page | What it does |
|------|-------------|
| **Dashboard** | Headline metrics, listings-by-role chart, **salary distribution histogram with click-through** (click a band to see the jobs in it), top skills, "New This Week" table, posting trend |
| **Job Explorer** | Browse all jobs with filters (role, seniority, salary, skills, AI involvement). Each listing shows salary, work mode, skills tags, and a direct apply link |

Older pages (Roles & Skills, AI Skills Deep Dive, Jobs For You, Company Leaderboard, Learning Roadmap, Market Pulse) are kept in the codebase but removed from navigation to keep the shared experience focused.

## Key Features

- **Salary distribution + click-through** — bar chart of monthly salary bands (<$5k → $20k+), click any band to see the jobs in it
- **MCF / FCF caveat banner** — every front-end surfaces the data scope honestly
- **Direct apply links** — every listing links back to the original MCF posting
- **Work mode indicators** — 🏠 Remote, 🔄 Hybrid, 🏢 Onsite
- **281-keyword AI taxonomy** — 11 categories across 3 career tiers, sourced from Stanford AI Index 2025, PwC, Lightcast

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Streamlit frontend | Streamlit, Plotly |
| Next.js frontend | Next.js 16, React 19, Recharts, Tailwind v4 |
| Database | Supabase (PostgreSQL) |
| AI Classification | OpenAI GPT-5-nano (JSON mode, configurable) |
| Data Source | MyCareersFuture.gov.sg (JSON API) |
| Automation | GitHub Actions (cron: daily at 2am UTC) |
| Hosting | Streamlit Community Cloud + Vercel |
| Language | Python 3.11+, TypeScript 5 |

## Setup

### 1. Clone & install

```bash
git clone https://github.com/toshtxg/sg-ai-job-scout.git
cd sg-ai-job-scout
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. Create Supabase tables

Go to your [Supabase Dashboard](https://supabase.com/dashboard) → SQL Editor → paste the contents of `sql/schema.sql` and run.

If you already have a live database, run `sql/migrations/2026-04-27-classified-listings-uniqueness.sql` first to deduplicate `classified_listings` and enforce one row per `listing_id`.

### 3. Set environment variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export OPENAI_API_KEY="sk-your-key"
```

Or create a `.env` file (see `.env.example`).

Optional tuning:

```bash
export OPENAI_CLASSIFIER_BATCH_SIZE="10"
```

### 4. Run the pipeline

```bash
python -m pipeline.run_pipeline
```

Scrapes jobs, classifies with GPT-5-nano by default, generates a market snapshot. Subsequent runs only process new/unclassified listings.

For manual backlog recovery:

```bash
python -m pipeline.backfill_unclassified --limit 250 --batch-size 10 --refresh-snapshot
```

### 5. Launch the dashboard

```bash
streamlit run app/Home.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Set **Main file path** to `app/Home.py`
4. Add secrets in app settings:
   ```toml
   SUPABASE_URL = "https://your-project.supabase.co"
   SUPABASE_KEY = "your-anon-key"
   OPENAI_API_KEY = "sk-your-key"
   ```

## GitHub Actions (Automated Scraping)

The pipeline runs automatically every day at 2 AM UTC.

1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add repository secrets: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
3. Optional overrides: `OPENAI_CLASSIFIER_MODEL`, `OPENAI_SUMMARY_MODEL`

You can also trigger manually from Actions → Scrape & Classify → Run workflow.

## Data Source & Caveats

- **[MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/)** — Singapore's government-mandated job portal (JSON API)
- 27 search terms covering data science, analytics, ML, AI, NLP, BI, and related fields
- ~2,100 listings classified across 11 role categories

**Important:** MCF is required posting under the [Fair Consideration Framework](https://www.mom.gov.sg/employment-practices/fair-consideration-framework) for jobs that may go to Employment Pass or S Pass holders. The dataset is therefore biased toward:

- Roles at salary tiers eligible for EP/S Pass
- Employers willing to hire foreign professionals
- Jobs not already filled via referral / internal mobility / executive search

It does **not** represent the full Singapore job market.

## Disclaimer

This project is for educational and research purposes. Job listing data is sourced from the MyCareersFuture.gov.sg public API. AI classification is approximate and may not perfectly categorize every listing. Salary data reflects what is posted and may not represent actual compensation.

## License

MIT
