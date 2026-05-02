# SG Data & AI Job Pulse Web App

This is the production frontend for SG Data & AI Job Pulse. It is a Next.js 16 App Router application deployed on Vercel.

- Production: [https://sg-data-jobs.vercel.app](https://sg-data-jobs.vercel.app)
- Companies: [https://sg-data-jobs.vercel.app/companies](https://sg-data-jobs.vercel.app/companies)

## Status

This is the live product surface. The repository's older Streamlit app is legacy/local reference only and is not the production solution.

## Stack

- Next.js 16
- React 19
- Tailwind CSS v4
- Recharts
- Supabase
- Vercel

## Routes

| Route | Purpose |
|-------|---------|
| `/` | Dashboard with market metrics, role mix, salary distribution, skills, new listings, and posting trend |
| `/jobs` | Filterable job explorer with direct MyCareersFuture links |
| `/companies` | Company leaderboard, company profiles, posting history, role mix, skill mix, and recent listings |

Additional analysis routes exist in the app directory, but the production navigation is focused on the routes above.

## Local Development

Install dependencies:

```bash
npm install
```

Create `web/.env.local`:

```bash
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_KEY="your-anon-key"
OPENAI_API_KEY="sk-your-key"
OPENAI_SUMMARY_MODEL="gpt-5-nano"
```

Run the dev server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Verification

```bash
npm run lint
npm run build
```

## Vercel Deployment

Vercel should be configured with:

- Framework preset: Next.js
- Root directory: `web`
- Build command: `npm run build`
- Install command: `npm install`
- Output directory: Next.js default

Required environment variables:

```bash
SUPABASE_URL
SUPABASE_KEY
OPENAI_API_KEY
OPENAI_SUMMARY_MODEL
```

The current production deployment is:

[https://sg-data-jobs.vercel.app](https://sg-data-jobs.vercel.app)
