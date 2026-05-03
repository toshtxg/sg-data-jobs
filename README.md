# SG Data & AI Job Pulse

A live look at Singapore's data, analytics, and AI job listings. Listings are sourced from [MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/), classified with GPT-5-nano, and served through a production Next.js dashboard on Vercel.

- **Production app:** [sg-data-jobs.vercel.app](https://sg-data-jobs.vercel.app/)
- **Companies view:** [sg-data-jobs.vercel.app/companies](https://sg-data-jobs.vercel.app/companies)

> **About the data.** MyCareersFuture is Singapore's government-mandated job portal. Under the [Fair Consideration Framework](https://www.mom.gov.sg/employment-practices/fair-consideration-framework), employers must post on MCF for at least 14 days before applying for an Employment Pass or S Pass. This dataset is therefore a **slice** of the SG market, skewed toward roles where employers are open to hiring foreign talent, not a complete picture.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Next.js](https://img.shields.io/badge/Next.js-16-black)
![Vercel](https://img.shields.io/badge/Hosting-Vercel-black)
![License](https://img.shields.io/badge/License-MIT-green)

## Current Direction

This repository is no longer positioned as a Streamlit solution. The production application lives in `web/` and is deployed on Vercel.

The older `app/` Streamlit code is retained only as legacy/local reference while the data pipeline and product surface continue to move through the Next.js app.

## Architecture

```
sg-data-jobs/
├── web/                          # Production Next.js 16 frontend on Vercel
│   ├── src/app/                  # App Router routes
│   ├── src/components/           # React UI, charts, tables, filters
│   └── src/lib/                  # Supabase loading, market helpers, taxonomy constants
├── pipeline/                     # Data pipeline shared by the app
│   ├── scrapers/
│   │   └── mycareersfuture.py    # MCF API scraper
│   ├── classifier.py             # GPT-5-nano structured classification
│   ├── ai_skills_analyzer.py     # AI skills taxonomy
│   ├── skills_normalizer.py      # Canonical skill name mapping
│   ├── snapshot.py               # Market snapshot aggregation
│   └── run_pipeline.py           # Pipeline orchestrator
├── app/                          # Legacy Streamlit prototype, not the live solution
├── sql/schema.sql                # Database DDL for Supabase
├── .github/workflows/scrape.yml  # Automated scraping
├── pyproject.toml
├── requirements.txt
└── .env.example
```

**Data flow:** MyCareersFuture API -> Supabase (`raw_listings`) -> GPT-5-nano classifier -> Supabase (`classified_listings`) -> snapshot aggregation -> Next.js dashboard on Vercel.

## Production Pages

| Page | Route | What it does |
|------|-------|--------------|
| Dashboard | `/` | Headline metrics, role mix, salary distribution, top skills, new listings, posting trend |
| Job Explorer | `/jobs` | Browse jobs with filters for role, seniority, salary, skills, and AI involvement |
| Companies | `/companies` | Company ranking, company profile, role/skill mix, posting history, and recent listings |

Additional analysis routes exist in the codebase for roles, AI skills, jobs-for-you, learning roadmap, and market pulse, but the production navigation is focused on the three routes above.

## Key Features

- **Company posting history** - compare company activity with daily, weekly, monthly, or yearly views
- **Salary distribution with click-through** - click a salary band to inspect the jobs behind it
- **MCF / FCF caveat banner** - every production page is explicit about data scope
- **Direct apply links** - listings link back to the original MCF posting
- **Work mode indicators** - Remote, Hybrid, Onsite, Unknown
- **AI skills taxonomy** - role and skills analysis for data, analytics, and AI work

## Tech Stack

| Component | Technology |
|-----------|------------|
| Production frontend | Next.js 16, React 19, Recharts, Tailwind CSS v4 |
| Hosting | Vercel |
| Database | Supabase (PostgreSQL) |
| AI classification | OpenAI GPT-5-nano |
| Data source | MyCareersFuture.gov.sg JSON API |
| Automation | GitHub Actions |
| Pipeline language | Python 3.11+ |

## Local Setup

### 1. Clone and install the pipeline

```bash
git clone https://github.com/toshtxg/sg-data-jobs.git
cd sg-data-jobs
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### 2. Create Supabase tables

Go to your [Supabase Dashboard](https://supabase.com/dashboard) -> SQL Editor -> paste the contents of `sql/schema.sql` and run.

If you already have a live database, run `sql/migrations/2026-04-27-classified-listings-uniqueness.sql` first to deduplicate `classified_listings` and enforce one row per `listing_id`.

### 3. Set pipeline environment variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"
export OPENAI_API_KEY="sk-your-key"
```

Or create a `.env` file from `.env.example`.

Optional tuning:

```bash
export OPENAI_CLASSIFIER_BATCH_SIZE="10"
```

### 4. Run the pipeline

```bash
python -m pipeline.run_pipeline
```

Scrapes jobs, classifies with GPT-5-nano by default, and generates a market snapshot. Subsequent runs only process new or unclassified listings.

For manual backlog recovery:

```bash
python -m pipeline.backfill_unclassified --limit 250 --batch-size 10 --refresh-snapshot
```

### 5. Run the production web app locally

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

The web app expects these environment variables in `web/.env.local` and in Vercel:

```bash
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
OPENAI_API_KEY="sk-your-key"
OPENAI_SUMMARY_MODEL="gpt-5-nano"
```

## Deploy on Vercel

The live product is deployed from `web/` to Vercel:

- Production URL: [https://sg-data-jobs.vercel.app](https://sg-data-jobs.vercel.app)
- Companies route: [https://sg-data-jobs.vercel.app/companies](https://sg-data-jobs.vercel.app/companies)

Vercel project settings:

- Framework preset: Next.js
- Root directory: `web`
- Build command: `npm run build`
- Install command: `npm install`
- Output directory: Next.js default

Set these Vercel environment variables:

```bash
SUPABASE_URL
SUPABASE_KEY
OPENAI_API_KEY
OPENAI_SUMMARY_MODEL
```

## GitHub Actions

The pipeline runs automatically every day at 2 AM UTC.

1. Go to the GitHub repo -> Settings -> Secrets and variables -> Actions
2. Add repository secrets: `SUPABASE_URL`, `SUPABASE_KEY`, `OPENAI_API_KEY`
3. Optional overrides: `OPENAI_CLASSIFIER_MODEL`, `OPENAI_SUMMARY_MODEL`

You can also trigger manually from Actions -> Scrape & Classify -> Run workflow.

## Data Source & Caveats

- **[MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/)** - Singapore's government-mandated job portal JSON API
- Search terms cover data science, analytics, ML, AI, NLP, BI, and related fields
- Classified listings are grouped into role categories, seniority levels, skills, AI involvement, work mode, and industry

**Important:** MCF posting is required under the [Fair Consideration Framework](https://www.mom.gov.sg/employment-practices/fair-consideration-framework) for jobs that may go to Employment Pass or S Pass holders. The dataset is therefore biased toward:

- Roles at salary tiers eligible for EP/S Pass
- Employers willing to hire foreign professionals
- Jobs not already filled through referral, internal mobility, or executive search

It does **not** represent the full Singapore job market.

## Disclaimer

This project is for educational and research purposes. Job listing data is sourced from the MyCareersFuture.gov.sg public API. AI classification is approximate and may not perfectly categorise every listing. Salary data reflects what is posted and may not represent actual compensation.

## License

MIT
