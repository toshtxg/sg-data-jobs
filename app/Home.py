import streamlit as st
from datetime import datetime, timezone

from app.utils.supabase_client import get_client

st.set_page_config(
    page_title="SG Data & AI Job Pulse",
    page_icon="\U0001f4ca",
    layout="wide",
    initial_sidebar_state="expanded",
)


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


@st.cache_data(ttl=300)
def _load_latest_pull_timestamp():
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


# Custom CSS
st.markdown(
    """<style>
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricLabel"] { font-size: 0.85rem; }
    [data-testid="stMetricValue"] { font-size: 1.4rem; }
    .stExpander { border: 1px solid #334155; border-radius: 8px; }
</style>""",
    unsafe_allow_html=True,
)

# Sidebar
with st.sidebar:
    latest_pull_timestamp = _load_latest_pull_timestamp()
    latest_pull_dt = _parse_utc_datetime(latest_pull_timestamp)
    if latest_pull_dt:
        pull_age = _format_age(datetime.now(timezone.utc) - latest_pull_dt)
        st.metric(
            label="Latest Data Pull (UTC)",
            value=f"{latest_pull_dt:%Y-%m-%d %H:%M}",
            delta=pull_age,
        )
    else:
        st.metric(
            label="Latest Data Pull (UTC)",
            value="Unknown",
        )
    st.markdown("---")

    st.markdown("## \U0001f4ca SG Data & AI Job Pulse")
    st.caption("A live look at Singapore's data, analytics & AI job listings")
    st.markdown("---")

    st.markdown("### About")
    st.markdown(
        "Tracks data, analytics and AI job listings in Singapore. "
        "LLMs classify unstructured job descriptions into structured, "
        "queryable data."
    )
    st.markdown("**Source:** MyCareersFuture.gov.sg")
    st.caption(
        "Heads up: MCF is the government-mandated portal for jobs that "
        "may go to Employment Pass / S Pass holders under the Fair "
        "Consideration Framework. It is a slice of the SG market — "
        "not the whole picture."
    )
    st.markdown(
        "**Methodology:** GPT-5-nano classifies each listing into role "
        "category, seniority, skills, and industry."
    )
    st.markdown(
        "**Schedule:** Pipeline runs daily at 2 AM UTC via "
        "GitHub Actions."
    )
    st.markdown("---")
    st.caption("Created by Tosh")

# Home page
st.markdown("# SG Data & AI Job Pulse")
st.markdown(
    "A live look at Singapore's data, analytics and AI job listings — "
    "structured from raw postings into queryable insights."
)

st.info(
    "**About the data.** Listings come from "
    "[MyCareersFuture.gov.sg](https://www.mycareersfuture.gov.sg/), "
    "Singapore's government-mandated job portal. Under the Fair "
    "Consideration Framework, employers must post here for at least "
    "14 days before applying for an Employment Pass or S Pass. "
    "This dataset is therefore a *slice* of the SG market — skewed "
    "toward roles where employers are open to hiring foreign talent — "
    "not a complete picture.",
    icon="ℹ️",
)

st.markdown("### Navigate")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/1_Dashboard.py", label="\U0001f4ca Dashboard", width="stretch")
with col2:
    st.page_link("pages/2_Job_Explorer.py", label="\U0001f50e Job Explorer", width="stretch")
