import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
from collections import Counter

import plotly.graph_objects as go

from app.utils.supabase_client import get_client

st.header("Companies")
st.markdown("Who's hiring data & AI talent in Singapore, and how often?")


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
                "role_category, seniority_level, technical_skills, requires_ai_ml, "
                "raw_listings!listing_id("
                "title, company, salary_min, salary_max, source_url, posting_date"
                ")"
            )
            .neq("role_category", "Other")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


raw_data = load_company_data()

if not raw_data:
    st.info(
        "No job data available yet. Data is refreshed automatically — check back soon!"
    )
    st.stop()

rows = []
for row in raw_data:
    raw = row.get("raw_listings") or {}
    company = (raw.get("company") or "Unknown").strip() or "Unknown"
    posting_date = raw.get("posting_date") or ""
    rows.append(
        {
            "company": company,
            "title": raw.get("title") or "Untitled",
            "role_category": row.get("role_category") or "Other",
            "seniority_level": row.get("seniority_level") or "Mid",
            "technical_skills": row.get("technical_skills") or [],
            "requires_ai_ml": row.get("requires_ai_ml", False),
            "salary_min": float(raw["salary_min"]) if raw.get("salary_min") is not None else None,
            "salary_max": float(raw["salary_max"]) if raw.get("salary_max") is not None else None,
            "source_url": raw.get("source_url") or "",
            "posting_date": posting_date,
            "posting_month": posting_date[:7] if posting_date else "",
        }
    )

df = pd.DataFrame(rows)

# ---------------------------------------------------------------------------
# Company rankings
# ---------------------------------------------------------------------------
company_counts = (
    df.groupby("company")
    .size()
    .reset_index(name="listings")
    .sort_values("listings", ascending=False)
    .reset_index(drop=True)
)

col_rank, col_profile = st.columns([1, 2], gap="medium")

with col_rank:
    st.subheader("Rankings")
    top20 = company_counts.head(20)
    fig_rank = go.Figure(
        go.Bar(
            x=top20["listings"],
            y=top20["company"],
            orientation="h",
            marker_color="#0ea5e9",
            text=top20["listings"],
            textposition="outside",
        )
    )
    fig_rank.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
        margin=dict(l=20, r=40, t=10, b=10),
        height=max(360, len(top20) * 28),
        yaxis=dict(autorange="reversed"),
        xaxis_title="Postings",
    )
    st.plotly_chart(fig_rank, use_container_width=True)

with col_profile:
    company_names = company_counts["company"].tolist()
    selected_company = st.selectbox(
        "Select a company",
        company_names,
        index=0,
        label_visibility="collapsed",
    )

    if selected_company:
        cdf = df[df["company"] == selected_company].copy()
        n = len(cdf)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total postings", n)

        top_role = cdf["role_category"].value_counts().index[0] if n else "N/A"
        m2.metric("Top role", top_role)

        skill_counter: Counter = Counter()
        for s_list in cdf["technical_skills"]:
            for s in s_list:
                skill_counter[s] += 1
        top_skill = skill_counter.most_common(1)[0][0] if skill_counter else "N/A"
        m3.metric("Top skill", top_skill)

        # --- Posting history timeline ---
        if cdf["posting_month"].notna().any() and (cdf["posting_month"] != "").any():
            timeline = (
                cdf[cdf["posting_month"] != ""]
                .groupby("posting_month")
                .size()
                .reset_index(name="count")
                .sort_values("posting_month")
            )
            timeline["label"] = pd.to_datetime(
                timeline["posting_month"], format="%Y-%m"
            ).dt.strftime("%b %y")

            if len(timeline) > 1:
                st.markdown("#### Posting History")
                colors = ["#0ea5e9"] * len(timeline)
                colors[-1] = "#14b8a6"  # highlight most recent month
                fig_timeline = go.Figure(
                    go.Bar(
                        x=timeline["label"],
                        y=timeline["count"],
                        marker_color=colors,
                        text=timeline["count"],
                        textposition="outside",
                    )
                )
                fig_timeline.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#fafafa"),
                    margin=dict(l=20, r=20, t=10, b=10),
                    height=200,
                    yaxis_title="Postings",
                    showlegend=False,
                )
                st.plotly_chart(fig_timeline, use_container_width=True)

        # --- Role breakdown ---
        st.markdown("#### Role Breakdown")
        role_counts = cdf["role_category"].value_counts().head(8)
        if not role_counts.empty:
            fig_roles = go.Figure(
                go.Bar(
                    x=role_counts.values.tolist(),
                    y=role_counts.index.tolist(),
                    orientation="h",
                    marker_color="#8b5cf6",
                    text=role_counts.values.tolist(),
                    textposition="outside",
                )
            )
            fig_roles.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#fafafa"),
                margin=dict(l=20, r=40, t=10, b=10),
                height=max(180, len(role_counts) * 30),
                yaxis=dict(autorange="reversed"),
            )
            st.plotly_chart(fig_roles, use_container_width=True)

# ---------------------------------------------------------------------------
# All postings table for selected company
# ---------------------------------------------------------------------------
if "selected_company" in dir() and selected_company:
    cdf_display = cdf.copy()
    cdf_display["Salary"] = cdf_display.apply(
        lambda r: (
            f"${r['salary_min']:,.0f}–${r['salary_max']:,.0f}"
            if pd.notna(r["salary_min"]) and pd.notna(r["salary_max"])
            else f"${r['salary_max']:,.0f}" if pd.notna(r["salary_max"])
            else f"${r['salary_min']:,.0f}" if pd.notna(r["salary_min"])
            else "—"
        ),
        axis=1,
    )
    display_cols = cdf_display[
        ["title", "role_category", "seniority_level", "Salary", "posting_date", "source_url"]
    ].rename(
        columns={
            "title": "Title",
            "role_category": "Role",
            "seniority_level": "Seniority",
            "posting_date": "Posted",
            "source_url": "Apply",
        }
    )
    display_cols = display_cols.sort_values("Posted", ascending=False)

    st.subheader(f"All postings — {selected_company}")
    st.dataframe(
        display_cols,
        use_container_width=True,
        hide_index=True,
        column_config={"Apply": st.column_config.LinkColumn("Apply", display_text="View →")},
    )
