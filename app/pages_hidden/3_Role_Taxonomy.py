import streamlit as st

st.set_page_config(layout="wide")

import pandas as pd
from collections import Counter

from app.utils.supabase_client import get_client
from app.components.charts import create_skills_heatmap
from app.components.filters import render_role_scope

st.header("Role Taxonomy & Skills")

selected_roles = render_role_scope(key="role_taxonomy")


@st.cache_data(ttl=3600)
def load_classified_data():
    client = get_client()
    all_data = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("role_category, seniority_level, technical_skills, industry")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_data.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_data


_all_data = load_classified_data()
data = [r for r in _all_data if not selected_roles or r.get("role_category") in selected_roles]

if not data:
    st.info(
        "No data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# --- Top Skills Bar Chart ---
st.subheader("Top Technical Skills")

skill_counter = Counter()
for row in data:
    for skill in row.get("technical_skills") or []:
        skill_counter[skill] += 1

if skill_counter:
    top_n = st.slider("Number of skills to show", 10, 50, 20)
    top_skills = skill_counter.most_common(top_n)

    import plotly.graph_objects as go

    fig = go.Figure(
        go.Bar(
            x=[count for _, count in top_skills],
            y=[skill for skill, _ in top_skills],
            orientation="h",
            marker_color="#0ea5e9",
            text=[count for _, count in top_skills],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
        margin=dict(l=20, r=20, t=20, b=20),
        height=max(400, top_n * 25),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")

# --- Skills Heatmap: Role vs Top Skills ---
st.subheader("Skills Heatmap by Role")

# Build role-skill matrix
role_skill_counts: dict[str, Counter] = {}
for row in data:
    role = row.get("role_category", "Other")
    if role not in role_skill_counts:
        role_skill_counts[role] = Counter()
    for skill in row.get("technical_skills") or []:
        role_skill_counts[role][skill] += 1

# Use top 15 skills globally
top_global_skills = [s for s, _ in skill_counter.most_common(15)]

if top_global_skills and role_skill_counts:
    heatmap_data = {}
    for role, counts in role_skill_counts.items():
        heatmap_data[role] = {skill: counts.get(skill, 0) for skill in top_global_skills}

    heatmap_df = pd.DataFrame(heatmap_data).T
    heatmap_df = heatmap_df.reindex(columns=top_global_skills)

    fig = create_skills_heatmap(heatmap_df)
    st.plotly_chart(fig, width="stretch")

