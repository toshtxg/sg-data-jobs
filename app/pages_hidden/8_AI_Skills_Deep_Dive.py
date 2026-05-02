import streamlit as st
import plotly.graph_objects as go
from collections import Counter

from app.utils.supabase_client import get_client
from app.components.filters import render_role_scope
from pipeline.ai_skills_analyzer import (
    analyze_all_listings,
    AI_SKILLS_TAXONOMY,
    SKILL_TIERS,
    SKILL_MATURITY,
)

st.set_page_config(layout="wide")

st.header("AI Skills Deep Dive")
st.caption(
    "What AI skills are Singapore employers actually asking for? "
    "Not just 'AI' broadly — the specific capabilities, tools, and frameworks."
)

selected_roles = render_role_scope(key="ai_deep_dive")

COLORS = {
    "AI Literacy & Augmentation": "#0ea5e9",
    "Prompt Engineering": "#38bdf8",
    "LLM & GenAI Development": "#14b8a6",
    "AI Agents & Automation": "#2dd4bf",
    "AI Evaluation & Safety": "#f59e0b",
    "Classical ML": "#8b5cf6",
    "Deep Learning": "#a78bfa",
    "NLP": "#ec4899",
    "Computer Vision": "#f97316",
    "MLOps & Infrastructure": "#84cc16",
    "Responsible AI & Governance": "#6366f1",
}


@st.cache_data(ttl=3600)
def load_and_analyze():
    client = get_client()

    # Get classified listings with descriptions
    all_data = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select(
                "id, listing_id, technical_skills, role_category, "
                "raw_listings!listing_id(description)"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        for row in resp.data:
            raw = row.get("raw_listings") or {}
            all_data.append(
                {
                    "id": row.get("id"),
                    "listing_id": row.get("listing_id"),
                    "description": raw.get("description", ""),
                    "technical_skills": row.get("technical_skills") or [],
                    "role_category": row.get("role_category", "Other"),
                }
            )
        if len(resp.data) < page_size:
            break
        offset += page_size

    return analyze_all_listings(all_data), all_data


_full_analysis, _full_data = load_and_analyze()

# Apply role filter
all_data = [r for r in _full_data if not selected_roles or r.get("role_category") in selected_roles]

if not all_data:
    st.info("No data available yet. Data is refreshed automatically on Mondays and Thursdays — check back soon!")
    st.stop()

# Re-analyze with filtered data
analysis = analyze_all_listings(all_data)

total = analysis["total_analyzed"]
with_ai = analysis["listings_with_ai"]
cat_counts = analysis["category_counts"]
cat_keywords = analysis["category_keywords"]

# ── Headline Metrics ──
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("Total Listings Analyzed", f"{total:,}")
col2.metric("Listings Mentioning AI Skills", f"{with_ai:,}")
col3.metric(
    "% Mentioning AI Skills",
    f"{with_ai / total * 100:.0f}%" if total else "0%",
)

# ── Main Chart: AI Skill Categories ──
st.markdown("### AI Skill Categories in Job Listings")
st.caption("How many listings mention keywords from each AI skill category")

if cat_counts:
    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1])
    cats = [c for c, _ in sorted_cats]
    counts = [n for _, n in sorted_cats]
    pcts = [n / total * 100 for n in counts]
    bar_colors = [COLORS.get(c, "#64748b") for c in cats]

    fig = go.Figure(
        go.Bar(
            y=cats,
            x=counts,
            orientation="h",
            marker_color=bar_colors,
            text=[f"{n} ({p:.0f}%)" for n, p in zip(counts, pcts)],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
        margin=dict(l=20, r=80, t=10, b=20),
        height=max(400, len(cats) * 40),
        xaxis_title="Number of Listings",
    )
    st.plotly_chart(fig, width="stretch")

# ── Tier Breakdown ──
st.markdown("### Skills by Career Tier")
st.caption(
    "Tier 1 = everyone needs these. Tier 2 = your core competitive edge. "
    "Tier 3 = specialist differentiation."
)

for tier_name, tier_categories in SKILL_TIERS.items():
    with st.expander(f"**{tier_name}**", expanded=True):
        for cat in tier_categories:
            count = cat_counts.get(cat, 0)
            pct = count / total * 100 if total else 0
            maturity = SKILL_MATURITY.get(cat, "")
            col1, col2, col3 = st.columns([3, 1, 3])
            col1.markdown(f"**{cat}**")
            col2.markdown(f"`{count}` ({pct:.0f}%)")
            col3.caption(maturity)

# ── Deep Dive: Keywords per Category ──
st.markdown("### What Employers Actually Say")
st.caption("The specific keywords and phrases found in job descriptions for each category")

selected_cat = st.selectbox(
    "Select a category to explore",
    list(AI_SKILLS_TAXONOMY.keys()),
)

keywords_for_cat = cat_keywords.get(selected_cat, {})
if keywords_for_cat:
    sorted_kw = sorted(keywords_for_cat.items(), key=lambda x: x[1], reverse=True)

    # Bar chart of keywords
    kw_names = [k for k, _ in sorted_kw[:20]]
    kw_counts = [c for _, c in sorted_kw[:20]]

    fig = go.Figure(
        go.Bar(
            y=kw_names[::-1],
            x=kw_counts[::-1],
            orientation="h",
            marker_color=COLORS.get(selected_cat, "#0ea5e9"),
            text=kw_counts[::-1],
            textposition="outside",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa"),
        margin=dict(l=20, r=60, t=10, b=20),
        height=max(300, len(kw_names) * 28),
        xaxis_title="Mentions",
        title=f"Top keywords for {selected_cat}",
    )
    st.plotly_chart(fig, width="stretch")

    # Context
    cat_count = cat_counts.get(selected_cat, 0)
    st.markdown(
        f"**{cat_count}** listings ({cat_count / total * 100:.1f}% of all jobs) "
        f"mention {selected_cat} skills."
    )
else:
    st.info(f"No keywords found for {selected_cat} in current listings.")

# ── AI Skills by Role ──
st.markdown("### AI Skills by Role Category")
st.caption("Which roles require which AI skill categories?")

# Build role × AI category matrix
role_ai_matrix: dict[str, Counter] = {}
for listing in all_data:
    role = listing.get("role_category", "Other")
    matches = {}
    combined = (listing.get("description") or "") + " " + " ".join(
        listing.get("technical_skills") or []
    )
    combined_lower = combined.lower()

    for category, keywords in AI_SKILLS_TAXONOMY.items():
        for kw in keywords:
            if kw in combined_lower:
                if role not in role_ai_matrix:
                    role_ai_matrix[role] = Counter()
                role_ai_matrix[role][category] += 1
                break  # Count each category once per listing per role

if role_ai_matrix:
    # Build heatmap
    all_cats = list(AI_SKILLS_TAXONOMY.keys())
    roles = sorted(role_ai_matrix.keys())

    z_vals = []
    for role in roles:
        row = [role_ai_matrix.get(role, Counter()).get(cat, 0) for cat in all_cats]
        z_vals.append(row)

    fig = go.Figure(
        go.Heatmap(
            z=z_vals,
            x=[c.replace(" & ", "\n& ") for c in all_cats],
            y=roles,
            colorscale=[[0, "#0e1117"], [0.5, "#0ea5e9"], [1, "#14b8a6"]],
            text=z_vals,
            texttemplate="%{text}",
            hovertemplate="Role: %{y}<br>AI Skill: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fafafa", size=11),
        margin=dict(l=20, r=20, t=10, b=20),
        height=max(400, len(roles) * 35 + 100),
        xaxis_tickangle=-45,
    )
    st.plotly_chart(fig, width="stretch")

# ── Methodology ──
with st.expander("Methodology"):
    st.markdown(
        """
This analysis scans each job listing's full description and extracted technical skills
against a curated taxonomy of **{}** keyword patterns across **{}** AI skill categories.

**Categories are organized into 3 tiers:**
- **Tier 1 (Foundational):** AI Literacy & Augmentation, Prompt Engineering
- **Tier 2 (Professional):** Classical ML, Deep Learning, NLP, MLOps, LLM/GenAI Development
- **Tier 3 (Specialist):** AI Agents, AI Evaluation & Safety, Computer Vision, Responsible AI

**Sources for taxonomy:** Stanford AI Index 2025, PwC AI Jobs Barometer, ManpowerGroup 2026
Talent Shortage Survey, Lightcast Global AI Skills Outlook, Singapore Budget 2026 AI initiatives.

A single listing can match multiple categories. "Surface AI" includes Tier 1 categories only.
"Deep AI" includes all others.
""".format(
            sum(len(v) for v in AI_SKILLS_TAXONOMY.values()),
            len(AI_SKILLS_TAXONOMY),
        )
    )
