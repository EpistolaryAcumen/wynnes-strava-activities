import os

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

_raw = os.environ["DATABASE_URL"]
_url = _raw.replace("postgresql://", "postgresql+psycopg://", 1) if _raw.startswith("postgresql://") else _raw.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(_url)


def pace_over_time_chart(since="2026-01-01"):
    """Mile-pace-over-time line chart, read from the curated warehouse table."""
    df = pd.read_sql(
        text(
            "SELECT start_ts, pace_min_per_mile, distance_mi "
            "FROM wynne_activities "
            "WHERE start_ts >= :since AND distance_mi > 3.09 "
            "ORDER BY start_ts"
        ),
        engine,
        params={"since": since},
    )

    # decimal minutes -> a datetime so Plotly can format the axis as MM:SS
    df["pace_dt"] = pd.to_datetime(df["pace_min_per_mile"], unit="m")

    fig = px.line(
        df,
        x="start_ts",
        y="pace_dt",
        markers=True,
        labels={"start_ts": "Date", "pace_dt": "Mile Pace"},
    )
    fig.update_yaxes(autorange="reversed", tickformat="%M:%S")   # faster on top
    fig.update_traces(hovertemplate="%{x|%b %d, %Y}<br>%{y|%M:%S}/mi<extra></extra>")
    fig.update_layout(template="plotly_white", height=500, margin=dict(t=10))
    return fig
