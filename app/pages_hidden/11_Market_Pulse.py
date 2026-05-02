import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from collections import Counter, defaultdict

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS, ROLE_COLORS
from app.components.filters import render_role_scope
from pipeline.ai_skills_analyzer import AI_SKILLS_TAXONOMY, analyze_all_listings

st.header("Market Pulse")
st.caption(
    "What's the overall AI job market landscape? Where are the opportunities?"
)

selected_roles = render_role_scope(key="market_pulse")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def load_market_data():
    """Load classified listings joined with raw_listings for full analysis."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, company, description, salary_min, salary_max, "
                "source_url, posting_date, source"
                ")"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


_all_market_data = load_market_data()
raw_data = [r for r in _all_market_data if not selected_roles or r.get("role_category") in selected_roles]

if not raw_data:
    st.info(
        "No job data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Build flat DataFrame
# ---------------------------------------------------------------------------
rows = []
for row in raw_data:
    raw = row.get("raw_listings") or {}
    company = (raw.get("company") or "Unknown").strip()
    if not company:
        company = "Unknown"
    rows.append(
        {
            "title": raw.get("title", "Untitled"),
            "company": company,
            "description": raw.get("description", ""),
            "salary_min": (
                float(raw["salary_min"])
                if raw.get("salary_min") is not None
                else None
            ),
            "salary_max": (
                float(raw["salary_max"])
                if raw.get("salary_max") is not None
                else None
            ),
            "technical_skills": row.get("technical_skills") or [],
            "role_category": row.get("role_category", "Other"),
            "seniority_level": row.get("seniority_level", "Mid"),
            "industry": row.get("industry", "Unknown"),
            "requires_ai_ml": row.get("requires_ai_ml", False),
            "remote_hybrid_onsite": row.get("remote_hybrid_onsite", "Unknown"),
        }
    )

df = pd.DataFrame(rows)

# Compute a usable salary column (midpoint where both exist, else whichever is available)
df["salary_mid"] = df.apply(
    lambda r: (
        (r["salary_min"] + r["salary_max"]) / 2
        if pd.notna(r["salary_min"]) and pd.notna(r["salary_max"])
        else r["salary_max"] if pd.notna(r["salary_max"])
        else r["salary_min"] if pd.notna(r["salary_min"])
        else None
    ),
    axis=1,
)

df_ai = df[df["requires_ai_ml"] == True]  # noqa: E712
df_non_ai = df[df["requires_ai_ml"] == False]  # noqa: E712


# =========================================================================
# Section 1: Market Overview Metrics
# =========================================================================
st.markdown("---")

total_listings = len(df)
ai_listings = len(df_ai)
ai_penetration = ai_listings / total_listings * 100 if total_listings else 0

ai_salary_vals = df_ai["salary_mid"].dropna()
non_ai_salary_vals = df_non_ai["salary_mid"].dropna()
median_ai_salary = ai_salary_vals.median() if not ai_salary_vals.empty else None
median_non_ai_salary = (
    non_ai_salary_vals.median() if not non_ai_salary_vals.empty else None
)

if median_ai_salary is not None and median_non_ai_salary and median_non_ai_salary > 0:
    salary_premium = (
        (median_ai_salary - median_non_ai_salary) / median_non_ai_salary * 100
    )
else:
    salary_premium = None

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Listings", f"{total_listings:,}")
col2.metric("AI/ML Listings", f"{ai_listings:,}")
col3.metric("% Mentioning AI/ML", f"{ai_penetration:.1f}%")

if median_ai_salary is not None and median_non_ai_salary is not None:
    col4.metric(
        "AI Salary Premium",
        f"{salary_premium:+.1f}%" if salary_premium is not None else "N/A",
        help=(
            f"Median AI salary: ${median_ai_salary:,.0f} vs "
            f"non-AI: ${median_non_ai_salary:,.0f}"
        ),
    )
else:
    col4.metric("AI Salary Premium", "N/A", help="Insufficient salary data")

# Show median salaries as a sub-row
sub1, sub2, sub3, sub4 = st.columns(4)
sub1.caption(f"AI median: ${median_ai_salary:,.0f}/mo" if median_ai_salary else "")
sub2.caption(
    f"Non-AI median: ${median_non_ai_salary:,.0f}/mo" if median_non_ai_salary else ""
)


# =========================================================================
# Section 2: Most In-Demand Skills
# =========================================================================
st.markdown("---")
st.subheader("Most In-Demand Skills")
st.caption(
    "Top 20 skills by number of listings. Bar shows demand; "
    "annotation shows how many distinct companies hire for each skill."
)

# Compute per-skill stats
skill_stats: dict[str, dict] = {}
for _, listing in df.iterrows():
    skills = listing["technical_skills"]
    company = listing["company"]
    for skill in skills:
        if skill not in skill_stats:
            skill_stats[skill] = {"count": 0, "companies": set()}
        skill_stats[skill]["count"] += 1
        skill_stats[skill]["companies"].add(company)

if skill_stats:
    top20 = sorted(skill_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:20]
    skill_names = [s for s, _ in top20]
    skill_counts = [v["count"] for _, v in top20]
    company_counts = [len(v["companies"]) for _, v in top20]

    fig = go.Figure(
        go.Bar(
            x=skill_counts[::-1],
            y=skill_names[::-1],
            orientation="h",
            marker_color="#0ea5e9",
            text=[
                f"{c} listings ({co} companies)"
                for c, co in zip(skill_counts[::-1], company_counts[::-1])
            ],
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Top 20 Skills by Demand",
        xaxis_title="Number of Listings",
        height=max(450, 20 * 28),
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("Not enough skill data.")


# =========================================================================
# Section 3: Industry AI Adoption
# =========================================================================
st.markdown("---")
st.subheader("Industry AI Adoption")
st.caption(
    "How deeply has AI hiring penetrated each industry? "
    "Compare total listings vs AI/ML listings by industry."
)

industry_stats = []
for industry, group in df.groupby("industry"):
    total_ind = len(group)
    ai_ind = group["requires_ai_ml"].sum()
    ai_pct = ai_ind / total_ind * 100 if total_ind else 0

    # Top 5 skills
    skill_counter = Counter()
    for skills_list in group["technical_skills"]:
        for s in skills_list:
            skill_counter[s] += 1
    top5_skills = ", ".join(s for s, _ in skill_counter.most_common(5))

    salary_vals = group["salary_mid"].dropna()
    avg_salary = salary_vals.mean() if not salary_vals.empty else None

    industry_stats.append(
        {
            "industry": industry,
            "total": total_ind,
            "ai_count": int(ai_ind),
            "ai_pct": ai_pct,
            "top_skills": top5_skills,
            "avg_salary": avg_salary,
        }
    )

ind_df = pd.DataFrame(industry_stats).sort_values("total", ascending=False)
# Keep only top 15 industries to avoid oversized chart
ind_df = ind_df.head(15).sort_values("total", ascending=True)

if not ind_df.empty:
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=ind_df["industry"],
            x=ind_df["total"],
            name="Total Listings",
            orientation="h",
            marker_color="#0ea5e9",
            text=ind_df["total"],
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=ind_df["industry"],
            x=ind_df["ai_count"],
            name="AI/ML Listings",
            orientation="h",
            marker_color="#14b8a6",
            text=ind_df["ai_count"],
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Total vs AI/ML Listings by Industry",
        xaxis_title="Number of Listings",
        barmode="group",
        height=min(600, max(400, len(ind_df) * 40 + 80)),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
        ),
    )
    st.plotly_chart(fig, width="stretch")

    # Expandable table with full details
    with st.expander("Full industry details"):
        table_df = ind_df.sort_values("total", ascending=False).copy()
        table_df["avg_salary"] = table_df["avg_salary"].apply(
            lambda v: f"${v:,.0f}" if pd.notna(v) else "N/A"
        )
        table_df["ai_pct"] = table_df["ai_pct"].apply(lambda v: f"{v:.1f}%")
        table_df = table_df.rename(
            columns={
                "industry": "Industry",
                "total": "Total Listings",
                "ai_count": "AI/ML Listings",
                "ai_pct": "AI %",
                "top_skills": "Top 5 Skills",
                "avg_salary": "Avg Salary",
            }
        )
        st.dataframe(table_df, width="stretch", hide_index=True)


