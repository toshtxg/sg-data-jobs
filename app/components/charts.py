import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

ROLE_COLORS = [
    "#0ea5e9", "#14b8a6", "#8b5cf6", "#f59e0b", "#ef4444",
    "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
    "#d946ef", "#64748b",
]

LAYOUT_DEFAULTS = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#fafafa"),
    margin=dict(l=20, r=20, t=40, b=20),
)


def create_listings_by_role_chart(listings_by_role: dict) -> go.Figure:
    """Horizontal bar chart of listings count by role category, sorted descending."""
    if not listings_by_role:
        return _empty_figure("No role data available")

    # Exclude "Other" — these are non-data/AI roles (software eng, DevOps, etc.)
    filtered = {r: c for r, c in listings_by_role.items() if r != "Other"}
    if not filtered:
        return _empty_figure("No role data available")

    # Sort by count descending
    sorted_items = sorted(filtered.items(), key=lambda x: x[1])
    roles = [r for r, _ in sorted_items]
    counts = [c for _, c in sorted_items]
    colors = [ROLE_COLORS[i % len(ROLE_COLORS)] for i in range(len(roles))]

    fig = go.Figure(
        go.Bar(
            y=roles,
            x=counts,
            orientation="h",
            marker_color=colors,
            text=counts,
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Listings by Role",
        xaxis_title="Count",
        yaxis_title="",
        height=max(350, len(roles) * 30 + 80),
    )
    return fig


def create_salary_comparison_chart(avg_salary_by_role: dict) -> go.Figure:
    """Horizontal bar chart comparing salary ranges by role."""
    if not avg_salary_by_role:
        return _empty_figure("No salary data available")

    roles = []
    avg_mins = []
    avg_maxs = []
    for role, data in sorted(
        avg_salary_by_role.items(), key=lambda x: x[1].get("avg_max") or 0
    ):
        if role == "Other":
            continue
        if data.get("avg_min") is not None or data.get("avg_max") is not None:
            roles.append(role)
            avg_mins.append(data.get("avg_min") or 0)
            avg_maxs.append(data.get("avg_max") or 0)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=roles,
            x=avg_mins,
            name="Avg Min",
            orientation="h",
            marker_color="#0ea5e9",
            text=[f"${v:,.0f}" for v in avg_mins],
            textposition="inside",
        )
    )
    fig.add_trace(
        go.Bar(
            y=roles,
            x=[m - n for m, n in zip(avg_maxs, avg_mins)],
            name="Avg Max (range)",
            orientation="h",
            marker_color="#14b8a6",
            text=[f"${v:,.0f}" for v in avg_maxs],
            textposition="inside",
            base=avg_mins,
        )
    )
    salary_layout = {k: v for k, v in LAYOUT_DEFAULTS.items() if k != "margin"}
    fig.update_layout(
        **salary_layout,
        title="Salary Range by Role (SGD/month)",
        barmode="overlay",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=60, b=20),
        height=max(300, len(roles) * 40 + 120),
    )
    return fig


def create_volume_over_time_chart(snapshots: list[dict]) -> go.Figure:
    """Line chart of total listing volume over time."""
    if not snapshots or len(snapshots) < 1:
        return _empty_figure("Need multiple pipeline runs to show trends")

    # Ensure dates are strings in YYYY-MM-DD format
    dates = [str(s["snapshot_date"])[:10] for s in snapshots]
    totals = [s.get("total_listings", 0) for s in snapshots]
    new_counts = [s.get("new_listings_count", 0) for s in snapshots]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=dates,
            y=totals,
            name="Total Listings",
            marker_color="#0ea5e9",
            text=totals,
            textposition="outside",
        )
    )
    fig.add_trace(
        go.Bar(
            x=dates,
            y=new_counts,
            name="New This Week",
            marker_color="#14b8a6",
            text=new_counts,
            textposition="outside",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        xaxis_title="Date",
        yaxis_title="Count",
        height=350,
        barmode="group",
        xaxis=dict(type="category", dtick=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    return fig


SALARY_BINS = [
    ("Under $5k", 0, 5000),
    ("$5k–$7k", 5000, 7000),
    ("$7k–$10k", 7000, 10000),
    ("$10k–$15k", 10000, 15000),
    ("$15k–$20k", 15000, 20000),
    ("$20k+", 20000, float("inf")),
]


def assign_salary_bin(salary_min, salary_max) -> str | None:
    """Pick a bin label using the midpoint of (min, max). Returns None if neither value is present."""
    values = [v for v in (salary_min, salary_max) if v is not None]
    if not values:
        return None
    midpoint = sum(float(v) for v in values) / len(values)
    for label, lo, hi in SALARY_BINS:
        if lo <= midpoint < hi:
            return label
    return None


def create_salary_distribution_chart(bin_counts: dict[str, int]) -> go.Figure:
    """Vertical bar chart of listing counts by salary bucket (SGD/month, midpoint)."""
    if not bin_counts or sum(bin_counts.values()) == 0:
        return _empty_figure("No salary data available")

    labels = [label for label, _, _ in SALARY_BINS]
    counts = [bin_counts.get(label, 0) for label in labels]
    colors = [ROLE_COLORS[i % len(ROLE_COLORS)] for i in range(len(labels))]

    fig = go.Figure(
        go.Bar(
            x=labels,
            y=counts,
            marker_color=colors,
            text=counts,
            textposition="outside",
            hovertemplate="%{x}<br>%{y} listings<extra></extra>",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Salary Distribution (SGD/month, midpoint)",
        xaxis_title="Monthly salary band",
        yaxis_title="Listings",
        height=380,
        clickmode="event+select",
    )
    return fig


def create_skills_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap of skills vs roles."""
    if df.empty:
        return _empty_figure("No skills data available")

    fig = go.Figure(
        go.Heatmap(
            z=df.values,
            x=df.columns.tolist(),
            y=df.index.tolist(),
            colorscale=[[0, "#0e1117"], [0.5, "#0ea5e9"], [1, "#14b8a6"]],
            text=df.values,
            texttemplate="%{text}",
            hovertemplate="Role: %{y}<br>Skill: %{x}<br>Count: %{z}<extra></extra>",
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Skills by Role",
        height=max(400, len(df) * 35 + 100),
        xaxis_tickangle=-45,
    )
    return fig


def create_sunburst_chart(df: pd.DataFrame) -> go.Figure:
    """Sunburst chart of role → seniority distribution."""
    if df.empty:
        return _empty_figure("No data available")

    fig = px.sunburst(
        df,
        path=["role_category", "seniority_level"],
        values="count",
        color_discrete_sequence=ROLE_COLORS,
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Role → Seniority Distribution",
        height=500,
    )
    return fig


def create_trends_by_role_chart(snapshots: list[dict]) -> go.Figure:
    """Line chart of listing counts by role over time."""
    if not snapshots or len(snapshots) < 2:
        return _empty_figure(
            "Need at least 2 pipeline runs to show trends"
        )

    fig = go.Figure()
    # Collect all roles across snapshots
    all_roles: set[str] = set()
    for s in snapshots:
        by_role = s.get("listings_by_role") or {}
        all_roles.update(by_role.keys())

    for i, role in enumerate(sorted(all_roles)):
        dates = []
        counts = []
        for s in snapshots:
            by_role = s.get("listings_by_role") or {}
            if role in by_role:
                dates.append(str(s["snapshot_date"])[:10])
                counts.append(by_role[role])
        if dates:
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=counts,
                    name=role,
                    mode="lines+markers",
                    line=dict(color=ROLE_COLORS[i % len(ROLE_COLORS)]),
                )
            )

    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Listings by Role Over Time",
        xaxis_title="Date",
        yaxis_title="Count",
        height=400,
        xaxis=dict(type="category"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def create_industry_pie_chart(industry_counts: dict) -> go.Figure:
    """Pie chart of industry breakdown."""
    if not industry_counts:
        return _empty_figure("No industry data available")

    fig = go.Figure(
        go.Pie(
            labels=list(industry_counts.keys()),
            values=list(industry_counts.values()),
            marker=dict(colors=ROLE_COLORS),
            hole=0.4,
        )
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        title="Industry Breakdown",
        height=400,
    )
    return fig


def _empty_figure(message: str) -> go.Figure:
    """Return a placeholder figure with a centered message."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color="#94a3b8"),
    )
    fig.update_layout(
        **LAYOUT_DEFAULTS,
        height=300,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig
