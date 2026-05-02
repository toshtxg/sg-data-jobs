import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
from datetime import date, datetime, timedelta, timezone

from app.utils.supabase_client import get_client
from app.components.charts import (
    SALARY_BINS,
    assign_salary_bin,
    create_listings_by_role_chart,
    create_salary_comparison_chart,
    create_salary_distribution_chart,
    create_volume_over_time_chart,
)
from app.components.metrics import render_metric_row

st.header("Dashboard")
st.caption(
    "Source: MyCareersFuture.gov.sg — the government-mandated portal "
    "for jobs that may go to Employment Pass / S Pass holders under the "
    "Fair Consideration Framework. A slice of the SG market, not the whole."
)


def _parse_posting_date(value):
    """Best-effort parse for Supabase date/datetime strings."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None


def _parse_utc_datetime(value):
    """Parse datetime text and normalize to UTC."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_age(delta):
    """Render a compact age label for freshness."""
    total_seconds = int(max(delta.total_seconds(), 0))
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d ago"
    if hours > 0:
        return f"{hours}h ago"
    return f"{minutes}m ago"


def _filter_recent_rows(rows, *, days=7):
    """Keep only rows posted in the last N days and sort newest first."""
    cutoff = datetime.now().date() - timedelta(days=days)
    filtered = []
    for row in rows or []:
        raw = row.get("raw_listings") or {}
        posting_date = _parse_posting_date(raw.get("posting_date"))
        if posting_date and posting_date >= cutoff:
            filtered.append(row)
    filtered.sort(
        key=lambda row: _parse_posting_date((row.get("raw_listings") or {}).get("posting_date")) or date.min,
        reverse=True,
    )
    return filtered


@st.cache_data(ttl=3600)
def load_dashboard_data():
    client = get_client()
    latest_snapshot = (
        client.table("market_snapshots")
        .select("*")
        .order("snapshot_date", desc=True)
        .limit(1)
        .execute()
    )
    all_snapshots = (
        client.table("market_snapshots")
        .select("*")
        .order("snapshot_date")
        .execute()
    )
    return latest_snapshot.data, all_snapshots.data


@st.cache_data(ttl=3600)
def load_recent_listings():
    """Load the most recent classified listings for 'New This Week'."""
    client = get_client()
    query = (
        client.table("classified_listings")
        .select(
            "role_category, seniority_level, remote_hybrid_onsite, "
            "raw_listings!listing_id(title, company, salary_min, salary_max, "
            "posting_date, source_url)"
        )
    )

    try:
        resp = query.order("classified_at", desc=True).limit(500).execute()
        return _filter_recent_rows(resp.data)
    except Exception:
        # Older deployed databases may not match the latest ordering column.
        # Fall back to an unordered fetch so the dashboard still renders.
        try:
            resp = query.limit(500).execute()
            return _filter_recent_rows(resp.data)
        except Exception:
            return []


@st.cache_data(ttl=3600)
def load_jobs_for_salary():
    """Load all classified listings with salary + role context for the salary histogram."""
    client = get_client()
    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "role_category, seniority_level, "
                "raw_listings!listing_id(title, company, salary_min, salary_max, "
                "posting_date, source_url)"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return rows


@st.cache_data(ttl=300)
def load_latest_pull_timestamp():
    """Load most recent scrape timestamp from raw listings."""
    client = get_client()
    latest_pull = (
        client.table("raw_listings")
        .select("scraped_at")
        .order("scraped_at", desc=True)
        .limit(1)
        .execute()
    )
    if not latest_pull.data:
        return None
    return latest_pull.data[0].get("scraped_at")


snapshot_data, all_snapshots = load_dashboard_data()
latest_pull_timestamp = load_latest_pull_timestamp()

if not snapshot_data:
    st.info(
        "No data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

latest = snapshot_data[0]
latest_pull_dt = _parse_utc_datetime(latest_pull_timestamp)
if latest_pull_dt:
    pull_age = _format_age(datetime.now(timezone.utc) - latest_pull_dt)
    st.sidebar.metric(
        label="Latest Data Pull (UTC)",
        value=f"{latest_pull_dt:%Y-%m-%d %H:%M}",
        delta=pull_age,
    )
    st.caption(f"Latest data pull: {latest_pull_dt:%Y-%m-%d %H:%M} UTC")
else:
    st.sidebar.metric(
        label="Latest Data Pull (UTC)",
        value="Unknown",
    )
    st.caption("Latest data pull: unknown")

# Extract top role and top skill
listings_by_role = latest.get("listings_by_role") or {}
filtered_roles = {r: c for r, c in listings_by_role.items() if r != "Other"}
top_role = max(filtered_roles, key=filtered_roles.get) if filtered_roles else "N/A"

top_skills = latest.get("top_skills") or []
top_skill = top_skills[0]["skill"] if top_skills else "N/A"

# Work mode summary from recent listings
recent = load_recent_listings()
work_modes = {}
for r in recent:
    wm = r.get("remote_hybrid_onsite", "Unknown")
    work_modes[wm] = work_modes.get(wm, 0) + 1
total_wm = sum(work_modes.values()) or 1
work_mode_str = " | ".join(
    f"{m} {c / total_wm * 100:.0f}%"
    for m, c in sorted(work_modes.items(), key=lambda x: -x[1])
    if m != "Unknown"
)

# Metrics row
render_metric_row(
    total=latest.get("total_listings", 0),
    new_this_week=latest.get("new_listings_count", 0),
    top_role=top_role,
    top_skill=top_skill,
)

if work_mode_str:
    st.caption(f"Work arrangements: {work_mode_str}")

st.markdown("")

# Charts
col1, col2 = st.columns(2)
with col1:
    other_count = listings_by_role.get("Other", 0)
    fig = create_listings_by_role_chart(listings_by_role)
    st.plotly_chart(fig, width="stretch")
    if other_count:
        st.caption(
            f"{other_count:,} non-data/AI listings (software eng, data center, "
            f"sales, etc.) excluded from chart."
        )

with col2:
    avg_salary = latest.get("avg_salary_by_role") or {}
    fig = create_salary_comparison_chart(avg_salary)
    st.plotly_chart(fig, width="stretch")

# --- Salary distribution (click a bar to filter) ---
st.markdown("### Salary Distribution")
salary_jobs_raw = load_jobs_for_salary()

binned_jobs: dict[str, list[dict]] = {label: [] for label, _, _ in SALARY_BINS}
no_salary_count = 0
for r in salary_jobs_raw:
    raw = r.get("raw_listings") or {}
    if r.get("role_category") == "Other":
        continue
    bin_label = assign_salary_bin(raw.get("salary_min"), raw.get("salary_max"))
    if bin_label is None:
        no_salary_count += 1
        continue
    binned_jobs[bin_label].append(
        {
            "Title": raw.get("title", ""),
            "Company": raw.get("company", "Unknown"),
            "Role": r.get("role_category", ""),
            "Seniority": r.get("seniority_level", ""),
            "Salary Min": raw.get("salary_min"),
            "Salary Max": raw.get("salary_max"),
            "Posted": raw.get("posting_date", ""),
            "Link": raw.get("source_url", ""),
        }
    )

bin_counts = {label: len(jobs) for label, jobs in binned_jobs.items()}
total_with_salary = sum(bin_counts.values())

salary_caption = (
    f"{total_with_salary:,} listings with salary disclosed · "
    f"{no_salary_count:,} listings did not disclose a salary range"
)
st.caption(salary_caption)

salary_fig = create_salary_distribution_chart(bin_counts)
selection = st.plotly_chart(
    salary_fig,
    width="stretch",
    on_select="rerun",
    selection_mode="points",
    key="salary_distribution_chart",
)

selected_bin = None
points = (selection or {}).get("selection", {}).get("points") if selection else None
if points:
    selected_bin = points[0].get("x")

if selected_bin and selected_bin in binned_jobs:
    bin_jobs = binned_jobs[selected_bin]
    st.markdown(f"#### {len(bin_jobs)} jobs in **{selected_bin}** band")
    if bin_jobs:
        bin_df = pd.DataFrame(
            [
                {
                    "Title": j["Title"],
                    "Company": j["Company"],
                    "Role": j["Role"],
                    "Seniority": j["Seniority"],
                    "Salary": (
                        f"${float(j['Salary Min']):,.0f}–${float(j['Salary Max']):,.0f}"
                        if j["Salary Min"] is not None and j["Salary Max"] is not None
                        else (
                            f"Up to ${float(j['Salary Max']):,.0f}"
                            if j["Salary Max"] is not None
                            else f"From ${float(j['Salary Min']):,.0f}"
                            if j["Salary Min"] is not None
                            else "—"
                        )
                    ),
                    "Posted": j["Posted"],
                    "Link": j["Link"],
                }
                for j in sorted(
                    bin_jobs,
                    key=lambda x: x.get("Posted") or "",
                    reverse=True,
                )[:50]
            ]
        )
        st.dataframe(
            bin_df,
            column_config={
                "Link": st.column_config.LinkColumn("Apply", display_text="View →"),
            },
            width="stretch",
            hide_index=True,
        )
        if len(bin_jobs) > 50:
            st.caption(f"Showing 50 of {len(bin_jobs)} jobs in this band.")
else:
    st.caption("Click a bar to see jobs in that salary band.")

# --- New This Week ---
st.markdown("### New This Week")

WORK_MODE_ICONS = {"Remote": "🏠", "Hybrid": "🔄", "Onsite": "🏢"}

new_rows = []
for r in recent:
    raw = r.get("raw_listings") or {}
    if not raw.get("title"):
        continue
    role = r.get("role_category", "Other")
    if role == "Other":
        continue
    sal_min = raw.get("salary_min")
    sal_max = raw.get("salary_max")
    salary = (
        f"${float(sal_min):,.0f}–${float(sal_max):,.0f}"
        if sal_min is not None and sal_max is not None
        else f"Up to ${float(sal_max):,.0f}" if sal_max is not None
        else "—"
    )
    wm = r.get("remote_hybrid_onsite", "Unknown")
    wm_icon = WORK_MODE_ICONS.get(wm, "")
    new_rows.append({
        "Title": raw.get("title", ""),
        "Company": raw.get("company", "Unknown"),
        "Role": role,
        "Seniority": r.get("seniority_level", ""),
        "Salary": salary,
        "Mode": f"{wm_icon} {wm}" if wm_icon else wm,
        "Posted": raw.get("posting_date", ""),
        "Link": raw.get("source_url", ""),
    })

if new_rows:
    new_df = pd.DataFrame(new_rows[:20])
    st.dataframe(
        new_df,
        column_config={
            "Link": st.column_config.LinkColumn("Apply", display_text="View →"),
        },
        width="stretch",
        hide_index=True,
    )
    if len(new_rows) > 20:
        st.caption(f"Showing 20 of {len(new_rows)} new listings. See Job Explorer for all.")
else:
    st.info("No new listings this week.")

# Volume over time — full width
fig = create_volume_over_time_chart(all_snapshots)
st.plotly_chart(fig, width="stretch")

# Top skills detail
if top_skills:
    st.markdown("### Top Technical Skills")
    cols = st.columns(5)
    for i, s in enumerate(top_skills[:15]):
        with cols[i % 5]:
            st.metric(s["skill"], s["count"])

# AI Market Summary
st.markdown("### AI Market Summary")


@st.cache_data(ttl=3600)
def generate_ai_summary(snapshot_json: str):
    """Generate a narrative market summary using GPT."""
    import json
    from app.utils.config import OPENAI_API_KEY, OPENAI_SUMMARY_MODEL

    if not OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        snapshot = json.loads(snapshot_json)
        prompt = f"""Based on this Singapore AI job market snapshot, write a concise 3-4 paragraph market briefing.
Be specific with numbers. Use a professional analyst tone.

Snapshot data:
- Total listings: {snapshot.get('total_listings', 0)}
- New this week: {snapshot.get('new_listings_count', 0)}
- Listings by role: {json.dumps(snapshot.get('listings_by_role', {}))}
- Listings by seniority: {json.dumps(snapshot.get('listings_by_seniority', {}))}
- Top skills: {json.dumps(snapshot.get('top_skills', [])[:15])}
- Avg salary by role: {json.dumps(snapshot.get('avg_salary_by_role', {}))}
- Snapshot date: {snapshot.get('snapshot_date', 'today')}"""

        response = client.chat.completions.create(
            model=OPENAI_SUMMARY_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Singapore tech job market analyst. Write clear, data-driven market briefings.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content
    except Exception:
        return None


import json as _json

summary = generate_ai_summary(_json.dumps(latest))
if summary:
    st.markdown(summary)
else:
    st.info(
        "AI summary unavailable. Set OPENAI_API_KEY to enable."
    )

# Last updated
created_at = latest.get("created_at", "")
if created_at:
    st.caption(f"Last updated: {created_at[:19].replace('T', ' ')} UTC")
