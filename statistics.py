import pandas as pd
from sqlalchemy import text

from charts import engine


def top_five_paces(since="2026-01-01"):
    """Return the five fastest runs (lowest mile pace) as display-ready rows."""
    df = pd.read_sql(
        text(
            "SELECT start_ts, pace_min_per_mile, distance_mi "
            "FROM wynne_activities "
            "WHERE start_ts >= :since AND pace_min_per_mile IS NOT NULL "
            "AND distance_mi > 3.09 "
            "ORDER BY pace_min_per_mile ASC "
            "LIMIT 5"
        ),
        engine,
        params={"since": since},
    )

    def fmt_pace(p):
        """Decimal minutes -> M:SS."""
        m = int(p)
        s = round((p - m) * 60)
        if s == 60:            # 7.999 -> 8:00, not 7:60
            m, s = m + 1, 0
        return f"{m}:{s:02d}"

    return [
        {
            "date": row.start_ts.strftime("%b %d, %Y"),
            "pace": fmt_pace(row.pace_min_per_mile),
            "distance": f"{row.distance_mi:.2f}",
        }
        for row in df.itertuples()
    ]


def half_marathon_count(since="2026-01-01"):
    """Number of runs with distance >= 13.1 miles."""
    row = pd.read_sql(
        text(
            "SELECT COUNT(*) AS cnt "
            "FROM wynne_activities "
            "WHERE start_ts >= :since AND distance_mi >= 13.1"
        ),
        engine,
        params={"since": since},
    )
    return int(row["cnt"].iloc[0])


def five_k_count(since="2026-01-01"):
    """Number of runs with distance >= 3.1 miles (5K)."""
    row = pd.read_sql(
        text(
            "SELECT COUNT(*) AS cnt "
            "FROM wynne_activities "
            "WHERE start_ts >= :since AND distance_mi >= 3.1"
        ),
        engine,
        params={"since": since},
    )
    return int(row["cnt"].iloc[0])


def total_distance(since="2026-01-01"):
    """Total miles run since the given date."""
    row = pd.read_sql(
        text(
            "SELECT COALESCE(SUM(distance_mi), 0) AS total "
            "FROM wynne_activities "
            "WHERE start_ts >= :since"
        ),
        engine,
        params={"since": since},
    )
    return round(float(row["total"].iloc[0]), 1)
