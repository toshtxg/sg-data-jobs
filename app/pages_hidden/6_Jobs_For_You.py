import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
from collections import Counter

from app.utils.supabase_client import get_client
from app.components.filters import render_role_scope, ROLE_CATEGORIES

st.header("Jobs for You")
st.markdown(
    "Enter your skills and target roles to find matching jobs — "
    "with salary, work mode, and direct apply links."
)

selected_roles = render_role_scope(key="jobs_for_you")

WORK_MODE_ICONS = {"Remote": "🏠", "Hybrid": "🔄", "Onsite": "🏢"}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def load_jobs():
    client = get_client()
    all_jobs = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "role_category, seniority_level, technical_skills, "
                "remote_hybrid_onsite, requires_ai_ml, "
                "raw_listings!listing_id("
                "title, company, salary_min, salary_max, "
                "posting_date, source_url"
                ")"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_jobs.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_jobs


_all_jobs = load_jobs()
jobs = [
    r for r in _all_jobs
    if (not selected_roles or r.get("role_category") in selected_roles)
    and r.get("role_category") != "Other"
]

if not jobs:
    st.info(
        "No job data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()


# ---------------------------------------------------------------------------
# Build skill universe
# ---------------------------------------------------------------------------

skill_counter = Counter()
for row in jobs:
    for s in row.get("technical_skills") or []:
        skill_counter[s] += 1

all_skills_sorted = [s for s, _ in skill_counter.most_common()]


# ---------------------------------------------------------------------------
# User input
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Your Skills")

col_multi, col_free = st.columns([3, 2])

with col_multi:
    selected_skills = st.multiselect(
        "Select skills from the database",
        all_skills_sorted,
        default=[],
        help="Skills that appear in job listings we have collected.",
    )

with col_free:
    free_text = st.text_input(
        "Additional skills (comma-separated)",
        placeholder="e.g. Python, SQL, Tableau",
    )

user_skills = set(s.strip() for s in selected_skills if s.strip())
if free_text:
    for s in free_text.split(","):
        s = s.strip()
        if s:
            user_skills.add(s)

if not user_skills:
    st.info("Add at least one skill above to find matching jobs.")
    st.stop()

st.markdown(
    "**Your skills:** " + ", ".join(f"`{s}`" for s in sorted(user_skills))
)

# Optional filters
with st.expander("Filters"):
    col_sen, col_wm = st.columns(2)
    with col_sen:
        seniority_filter = st.multiselect(
            "Seniority",
            ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"],
        )
    with col_wm:
        work_mode_filter = st.multiselect(
            "Work Mode",
            ["Remote", "Hybrid", "Onsite"],
        )

st.markdown("---")


# ---------------------------------------------------------------------------
# Matching logic
# ---------------------------------------------------------------------------


def compute_match(listing_skills: list, user_skills: set) -> tuple[int, int, float]:
    """Return (matched, total, pct) for a listing vs user skills."""
    listing_set = {s.lower() for s in listing_skills if s}
    user_lower = {s.lower() for s in user_skills}
    if not listing_set:
        return 0, 0, 0.0
    matched = len(listing_set & user_lower)
    return matched, len(listing_set), matched / len(listing_set)


# Score all jobs
scored = []
for row in jobs:
    raw = row.get("raw_listings") or {}
    if not raw.get("title"):
        continue

    tech_skills = row.get("technical_skills") or []
    matched, total, pct = compute_match(tech_skills, user_skills)

    if matched == 0:
        continue  # No overlap at all

    # Apply optional filters
    if seniority_filter and row.get("seniority_level") not in seniority_filter:
        continue
    if work_mode_filter and row.get("remote_hybrid_onsite") not in work_mode_filter:
        continue

    sal_min = raw.get("salary_min")
    sal_max = raw.get("salary_max")
    salary = (
        f"${float(sal_min):,.0f}–${float(sal_max):,.0f}"
        if sal_min is not None and sal_max is not None
        else f"Up to ${float(sal_max):,.0f}" if sal_max is not None
        else "—"
    )

    wm = row.get("remote_hybrid_onsite", "Unknown")
    wm_icon = WORK_MODE_ICONS.get(wm, "")

    scored.append({
        "match_pct": pct,
        "matched": matched,
        "total": total,
        "title": raw.get("title", ""),
        "company": raw.get("company", "Unknown"),
        "role": row.get("role_category", ""),
        "seniority": row.get("seniority_level", ""),
        "salary": salary,
        "work_mode": f"{wm_icon} {wm}" if wm_icon else wm,
        "posted": raw.get("posting_date", ""),
        "link": raw.get("source_url", ""),
        "skills": tech_skills,
        "user_lower": {s.lower() for s in user_skills},
    })

# Sort by match percentage descending, then by posting date
scored.sort(key=lambda x: (-x["match_pct"], x["posted"] or ""), reverse=False)
scored.sort(key=lambda x: x["match_pct"], reverse=True)


# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------

strong_matches = [s for s in scored if s["match_pct"] >= 0.5]
partial_matches = [s for s in scored if 0 < s["match_pct"] < 0.5]

st.subheader(f"Strong Matches ({len(strong_matches)})")
st.caption("You have 50%+ of the required skills")

if strong_matches:
    for job in strong_matches[:50]:
        match_label = f"{job['match_pct']:.0%} match ({job['matched']}/{job['total']} skills)"

        header = f"**{job['title']}** — {job['company']}"
        if job["salary"] != "—":
            header += f"  |  {job['salary']}"
        header += f"  |  {match_label}"

        with st.expander(header):
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            col1.markdown(f"**Role:** {job['role']}")
            col2.markdown(f"**Seniority:** {job['seniority']}")
            col3.markdown(f"**{job['work_mode']}** | Posted: {job['posted']}")
            if job["link"]:
                col4.link_button("Apply →", job["link"])

            # Skills with have/missing highlighting
            skills_html = ""
            for s in job["skills"]:
                if s.lower() in job["user_lower"]:
                    skills_html += (
                        f'<span style="background:#065f46;border:1px solid #10b981;'
                        f'border-radius:12px;padding:2px 10px;margin:2px;'
                        f'display:inline-block;font-size:0.85rem;">{s}</span>'
                    )
                else:
                    skills_html += (
                        f'<span style="background:#7f1d1d;border:1px solid #ef4444;'
                        f'border-radius:12px;padding:2px 10px;margin:2px;'
                        f'display:inline-block;font-size:0.85rem;">{s}</span>'
                    )
            st.markdown(skills_html, unsafe_allow_html=True)
            st.caption("Green = you have | Red = you're missing")

    if len(strong_matches) > 50:
        st.caption(f"Showing 50 of {len(strong_matches)} strong matches.")
else:
    st.info(
        "No strong matches yet. Try adding more skills or broadening your role scope."
    )

st.markdown("---")
st.subheader(f"Partial Matches ({len(partial_matches)})")
st.caption("You have some of the required skills — worth exploring")

if partial_matches:
    # Show as a compact table
    partial_rows = []
    for job in partial_matches[:30]:
        partial_rows.append({
            "Title": job["title"],
            "Company": job["company"],
            "Role": job["role"],
            "Match": f"{job['match_pct']:.0%}",
            "Salary": job["salary"],
            "Mode": job["work_mode"],
            "Posted": job["posted"],
            "Link": job["link"],
        })

    partial_df = pd.DataFrame(partial_rows)
    st.dataframe(
        partial_df,
        column_config={
            "Link": st.column_config.LinkColumn("Apply", display_text="View →"),
        },
        width="stretch",
        hide_index=True,
    )
    if len(partial_matches) > 30:
        st.caption(f"Showing 30 of {len(partial_matches)} partial matches.")
else:
    st.info("No partial matches found.")

# ---------------------------------------------------------------------------
# Skills to close the gap
# ---------------------------------------------------------------------------
if strong_matches or partial_matches:
    st.markdown("---")
    st.subheader("Skills to Learn Next")
    st.caption(
        "The most common skills in your matched jobs that you don't have yet."
    )

    missing_counter = Counter()
    user_lower = {s.lower() for s in user_skills}
    for job in scored:
        for s in job["skills"]:
            if s.lower() not in user_lower:
                missing_counter[s] += 1

    top_missing = missing_counter.most_common(10)
    if top_missing:
        for rank, (skill, count) in enumerate(top_missing, 1):
            st.markdown(
                f"**{rank}. {skill}** — appears in {count} of your matched jobs"
            )
