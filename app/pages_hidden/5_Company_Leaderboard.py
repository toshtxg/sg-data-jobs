import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
from collections import Counter

import plotly.graph_objects as go
import plotly.express as px

from app.utils.supabase_client import get_client
from app.components.filters import render_role_scope

st.header("Company Leaderboard")
st.markdown("Which companies hire the most AI talent in Singapore?")

selected_roles = render_role_scope(key="company_leaderboard")


@st.cache_data(ttl=3600)
def load_company_data():
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "*, raw_listings!listing_id("
                "title, company, salary_min, salary_max, "
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


_all_company_data = load_company_data()
data = [r for r in _all_company_data if not selected_roles or r.get("role_category") in selected_roles]

if not data:
    st.info(
        "No job data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Build a flat DataFrame for analysis
# ---------------------------------------------------------------------------
rows = []
for row in data:
    raw = row.get("raw_listings") or {}
    company = raw.get("company") or "Unknown"
    if not company or company.strip() == "":
        company = "Unknown"
    rows.append(
        {
            "company": company.strip(),
            "title": raw.get("title", "Untitled"),
            "role_category": row.get("role_category", "Other"),
            "seniority_level": row.get("seniority_level", "Mid"),
            "salary_min": float(raw["salary_min"]) if raw.get("salary_min") is not None else None,
            "salary_max": float(raw["salary_max"]) if raw.get("salary_max") is not None else None,
            "technical_skills": row.get("technical_skills") or [],
            "industry": row.get("industry", "N/A"),
            "requires_ai_ml": row.get("requires_ai_ml", False),
            "remote_hybrid_onsite": row.get("remote_hybrid_onsite", "Unknown"),
            "source_url": raw.get("source_url", ""),
            "posting_date": raw.get("posting_date", ""),
            "source": raw.get("source", ""),
        }
    )

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Company Rankings Table
# ---------------------------------------------------------------------------
st.subheader("Company Rankings")


def _top_items(series, n=3):
    """Return the top-n most common values as a comma-separated string."""
    counts = series.value_counts()
    return ", ".join(counts.head(n).index.tolist())


def _top_skills(skills_lists, n=3):
    """Return top-n skills across a column of skill lists."""
    counter = Counter()
    for skills in skills_lists:
        for s in skills:
            counter[s] += 1
    return ", ".join(s for s, _ in counter.most_common(n))


def _format_salary(val):
    if pd.isna(val):
        return "N/A"
    return f"${val:,.0f}"


company_stats = (
    df.groupby("company")
    .agg(
        listings=("title", "size"),
        top_roles=("role_category", _top_items),
        avg_salary_min=("salary_min", "mean"),
        avg_salary_max=("salary_max", "mean"),
        top_skills=("technical_skills", _top_skills),
    )
    .sort_values("listings", ascending=False)
    .reset_index()
)

company_stats["avg_salary_range"] = company_stats.apply(
    lambda r: (
        f"{_format_salary(r['avg_salary_min'])} - {_format_salary(r['avg_salary_max'])}"
        if pd.notna(r["avg_salary_min"]) or pd.notna(r["avg_salary_max"])
        else "N/A"
    ),
    axis=1,
)

display_df = company_stats[
    ["company", "listings", "top_roles", "avg_salary_range", "top_skills"]
].rename(
    columns={
        "company": "Company",
        "listings": "# Listings",
        "top_roles": "Top Roles",
        "avg_salary_range": "Avg Salary Range",
        "top_skills": "Top Skills",
    }
)

st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    height=min(len(display_df) * 35 + 40, 600),
)

# ---------------------------------------------------------------------------
# Bar Chart — Top 20 Companies by Listing Count
# ---------------------------------------------------------------------------
st.subheader("Top 20 Companies by Listing Count")

top20 = company_stats.head(20).copy()

fig = go.Figure(
    go.Bar(
        x=top20["listings"],
        y=top20["company"],
        orientation="h",
        marker_color="#0ea5e9",
        text=top20["listings"],
        textposition="outside",
    )
)
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#fafafa"),
    margin=dict(l=20, r=40, t=20, b=20),
    height=max(400, len(top20) * 30),
    yaxis=dict(autorange="reversed"),
    xaxis_title="Number of Listings",
)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Company Profile — select a company for deep-dive
# ---------------------------------------------------------------------------
st.subheader("Company Profile")

company_names = company_stats["company"].tolist()
selected_company = st.selectbox(
    "Select a company to view its profile",
    company_names,
    index=0,
)

if selected_company:
    company_df = df[df["company"] == selected_company]
    n_listings = len(company_df)

    # Header metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Open Listings", n_listings)

    salary_vals = company_df["salary_max"].dropna()
    if not salary_vals.empty:
        col2.metric("Avg Max Salary", f"${salary_vals.mean():,.0f}/mo")
    else:
        col2.metric("Avg Max Salary", "N/A")

    ai_ml_pct = (
        company_df["requires_ai_ml"].sum() / n_listings * 100 if n_listings else 0
    )
    col3.metric("AI/ML Required", f"{ai_ml_pct:.0f}%")

    # --- All Open Roles ---
    WORK_MODE_ICONS = {"Remote": "🏠", "Hybrid": "🔄", "Onsite": "🏢"}
    st.markdown("#### Open Roles")
    roles_display = company_df[
        ["title", "role_category", "seniority_level", "salary_min", "salary_max",
         "remote_hybrid_onsite", "posting_date", "source_url"]
    ].copy()
    roles_display["Salary"] = roles_display.apply(
        lambda r: (
            f"${r['salary_min']:,.0f}–${r['salary_max']:,.0f}"
            if pd.notna(r["salary_min"]) and pd.notna(r["salary_max"])
            else f"${r['salary_max']:,.0f}" if pd.notna(r["salary_max"])
            else f"${r['salary_min']:,.0f}" if pd.notna(r["salary_min"])
            else "—"
        ),
        axis=1,
    )
    roles_display["Mode"] = roles_display["remote_hybrid_onsite"].apply(
        lambda wm: f"{WORK_MODE_ICONS.get(wm, '')} {wm}".strip() if wm else "Unknown"
    )
    roles_display = roles_display.drop(columns=["salary_min", "salary_max", "remote_hybrid_onsite"])
    roles_display = roles_display.rename(
        columns={
            "title": "Title",
            "role_category": "Role Category",
            "seniority_level": "Seniority",
            "posting_date": "Posted",
            "source_url": "Apply",
        }
    )
    roles_display = roles_display[["Title", "Role Category", "Seniority", "Salary", "Mode", "Posted", "Apply"]]
    roles_display = roles_display.sort_values("Posted", ascending=False)
    st.dataframe(
        roles_display,
        width="stretch",
        hide_index=True,
        column_config={"Apply": st.column_config.LinkColumn("Apply", display_text="View →")},
    )

    # --- Salary Distribution ---
    st.markdown("#### Salary Distribution")
    salary_data = company_df.dropna(subset=["salary_min", "salary_max"])
    if salary_data.empty:
        st.info("No salary data available for this company.")
    else:
        fig_salary = go.Figure()
        fig_salary.add_trace(
            go.Box(
                x=salary_data["salary_min"],
                name="Salary Min",
                marker_color="#0ea5e9",
                boxmean=True,
            )
        )
        fig_salary.add_trace(
            go.Box(
                x=salary_data["salary_max"],
                name="Salary Max",
                marker_color="#14b8a6",
                boxmean=True,
            )
        )
        fig_salary.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fafafa"),
            margin=dict(l=20, r=20, t=20, b=20),
            xaxis_title="SGD/month",
            height=300,
            showlegend=True,
        )
        st.plotly_chart(fig_salary, width="stretch")

    # --- Most Requested Skills ---
    st.markdown("#### Most Requested Skills")
    skill_counter = Counter()
    for skills in company_df["technical_skills"]:
        for s in skills:
            skill_counter[s] += 1

    if skill_counter:
        top_skills = skill_counter.most_common(15)
        fig_skills = go.Figure(
            go.Bar(
                x=[count for _, count in top_skills],
                y=[skill for skill, _ in top_skills],
                orientation="h",
                marker_color="#14b8a6",
                text=[count for _, count in top_skills],
                textposition="outside",
            )
        )
        fig_skills.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fafafa"),
            margin=dict(l=20, r=40, t=20, b=20),
            height=max(300, len(top_skills) * 28),
            yaxis=dict(autorange="reversed"),
            xaxis_title="Number of Listings",
        )
        st.plotly_chart(fig_skills, width="stretch")
    else:
        st.info("No skill data available for this company.")

    # --- Role Category Breakdown ---
    st.markdown("#### Role Category Breakdown")
    role_counts = company_df["role_category"].value_counts()
    if not role_counts.empty:
        fig_roles = go.Figure(
            go.Pie(
                labels=role_counts.index.tolist(),
                values=role_counts.values.tolist(),
                hole=0.4,
                marker=dict(
                    colors=[
                        "#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b",
                        "#ef4444", "#ec4899", "#06b6d4", "#84cc16",
                    ]
                ),
                textinfo="label+percent",
                textfont=dict(color="#fafafa"),
            )
        )
        fig_roles.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#fafafa"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=400,
            showlegend=True,
        )
        st.plotly_chart(fig_roles, width="stretch")
    else:
        st.info("No role category data available for this company.")
