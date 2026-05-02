import streamlit as st

st.set_page_config(layout="wide")

import plotly.graph_objects as go
from collections import Counter, defaultdict

from app.utils.supabase_client import get_client
from app.components.charts import LAYOUT_DEFAULTS
from app.components.filters import render_role_scope

st.header("Learning Roadmap")
st.caption(
    "What should you learn and in what order? "
    "See how skill requirements change with seniority, and get a personalised "
    "learning path for your target role."
)

selected_roles = render_role_scope(key="learning_roadmap")

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

SENIORITY_ORDER = ["Junior", "Mid", "Senior", "Lead", "Principal", "Director"]


@st.cache_data(ttl=3600)
def load_listings():
    """Load classified listings with role, seniority, skills, and AI flag."""
    client = get_client()
    all_rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            client.table("classified_listings")
            .select("role_category, seniority_level, technical_skills, requires_ai_ml")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        all_rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return all_rows


_all_listings = load_listings()
listings = [r for r in _all_listings if not selected_roles or r.get("role_category") in selected_roles]

if not listings:
    st.info(
        "No data available yet. Data is refreshed automatically on "
        "Mondays and Thursdays — check back soon!"
    )
    st.stop()

# ---------------------------------------------------------------------------
# Pre-compute shared data structures
# ---------------------------------------------------------------------------


@st.cache_data(ttl=3600)
def build_roadmap_data(_listings):
    """Build data structures used across all sections."""
    # Per-seniority skill counts and totals
    seniority_skill_counts = {}
    seniority_totals = Counter()

    # Per-role+seniority skill counts
    role_seniority_skill_counts = {}
    role_seniority_totals = defaultdict(Counter)

    # Global skill counter for top-N selection
    global_skill_counter = Counter()

    # Listing-level skill sets for co-occurrence
    all_skill_sets = []

    for row in _listings:
        seniority = row.get("seniority_level") or "Mid"
        role = row.get("role_category") or "Other"
        skills = row.get("technical_skills") or []
        skills_set = set(s.strip() for s in skills if s and s.strip())

        if not skills_set:
            continue

        all_skill_sets.append(skills_set)

        # Seniority-level aggregation
        seniority_totals[seniority] += 1
        if seniority not in seniority_skill_counts:
            seniority_skill_counts[seniority] = Counter()
        for s in skills_set:
            seniority_skill_counts[seniority][s] += 1
            global_skill_counter[s] += 1

        # Role + seniority aggregation
        key = (role, seniority)
        role_seniority_totals[role][seniority] += 1
        if key not in role_seniority_skill_counts:
            role_seniority_skill_counts[key] = Counter()
        for s in skills_set:
            role_seniority_skill_counts[key][s] += 1

    return (
        seniority_skill_counts,
        dict(seniority_totals),
        role_seniority_skill_counts,
        dict(role_seniority_totals),
        global_skill_counter,
        all_skill_sets,
    )


(
    seniority_skill_counts,
    seniority_totals,
    role_seniority_skill_counts,
    role_seniority_totals,
    global_skill_counter,
    all_skill_sets,
) = build_roadmap_data(listings)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════
# Section 1: Skill Progression by Seniority
# ═══════════════════════════════════════════════════════════════════════════

st.subheader("1. Skill Progression by Seniority")
st.markdown(
    "Which skills become more or less important as you advance? "
    "Cell values show the percentage of listings at each seniority level "
    "that mention the skill."
)

# Collect top 15 skills per seniority, then take the union
active_levels = [lvl for lvl in SENIORITY_ORDER if lvl in seniority_skill_counts]

if active_levels:
    union_skills = set()
    for lvl in active_levels:
        top15 = [s for s, _ in seniority_skill_counts[lvl].most_common(15)]
        union_skills.update(top15)

    # Sort skills by overall frequency descending for a stable row order
    sorted_skills = sorted(
        union_skills, key=lambda s: global_skill_counter.get(s, 0), reverse=True
    )

    # Build percentage matrix: rows = skills, columns = seniority levels
    z_values = []
    text_values = []
    for skill in sorted_skills:
        row_z = []
        row_t = []
        for lvl in active_levels:
            total = seniority_totals.get(lvl, 0)
            count = seniority_skill_counts.get(lvl, Counter()).get(skill, 0)
            pct = (count / total * 100) if total > 0 else 0
            row_z.append(round(pct, 1))
            row_t.append(f"{pct:.0f}%")
        z_values.append(row_z)
        text_values.append(row_t)

    fig = go.Figure(
        go.Heatmap(
            z=z_values,
            x=active_levels,
            y=sorted_skills,
            colorscale=[[0, "#0e1117"], [0.5, "#0ea5e9"], [1, "#14b8a6"]],
            text=text_values,
            texttemplate="%{text}",
            hovertemplate=(
                "Skill: %{y}<br>Seniority: %{x}<br>"
                "Frequency: %{text}<extra></extra>"
            ),
            colorbar=dict(title="% of listings"),
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Skill Frequency (%) by Seniority Level",
        height=max(500, len(sorted_skills) * 28 + 100),
        xaxis=dict(side="top"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")
else:
    st.info("No seniority data available.")


# ---------------------------------------------------------------------------
# Disclaimer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "**Note:** This roadmap is derived from patterns in Singapore job listings "
    "and reflects employer demand, not an exhaustive curriculum. Skill frequency "
    "percentages are based on the subset of listings that mention each seniority "
    "level or role category."
)
