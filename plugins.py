import os
import time
from datetime import timezone

import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()
url = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_engine(url)


# Secrets come from the environment (.env locally, injected vars on Railway) —
# never hard-code client_secret / refresh_token in a committed file.
credentials = {
    "client_id": os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
}


def connect_to_strava(credentials):
    """Exchange a refresh token for an access token and return auth headers."""
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={**credentials, "grant_type": "refresh_token"},
    )
    response.raise_for_status()
    access_token = response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def fetch_activities(headers):
    """Fetch ALL athlete activities from Strava, paging until exhausted."""
    all_activities = []
    page = 1
    while True:
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=headers,
            params={"per_page": 200, "page": page},
        )
        response.raise_for_status()
        batch = response.json()
        if not batch:            # empty page = no more activities
            break
        all_activities.extend(batch)
        print(f"page {page}: fetched {len(batch)} (total {len(all_activities)})")
        page += 1
        time.sleep(1)

    return pd.json_normalize(all_activities)


def create_wynne_activities_table(engine, all_activities):
    all_activities["start_lat"] = all_activities["start_latlng"].str[0]
    all_activities["start_lng"] = all_activities["start_latlng"].str[1]

    all_activities.to_sql("all_activities_raw", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.exec_driver_sql("""
            DROP TABLE IF EXISTS wynne_activities;
            CREATE TABLE wynne_activities (
                id                   BIGINT PRIMARY KEY,
                name                 TEXT,
                sport_type           TEXT,
                start_ts             TIMESTAMP,
                distance_mi          DOUBLE PRECISION,
                moving_min           DOUBLE PRECISION,
                total_elevation_gain DOUBLE PRECISION,
                pace_min_per_mile    DOUBLE PRECISION,
                summary_polyline     TEXT,
                start_lat            DOUBLE PRECISION,
                start_lng            DOUBLE PRECISION
            );
        """)
        conn.exec_driver_sql("""
            INSERT INTO wynne_activities
            SELECT
                id, name, sport_type,
                CAST(start_date_local AS TIMESTAMP),
                ROUND((distance / 1609.344)::numeric, 2),
                ROUND((moving_time / 60.0)::numeric, 2),
                total_elevation_gain,
                CASE WHEN distance > 0
                     THEN ROUND(((moving_time/60.0)/(distance/1609.344))::numeric, 2)
                END,
                "map.summary_polyline",
                start_lat,
                start_lng
            FROM all_activities_raw;
        """)


def get_recent_date(engine):
    with engine.connect() as conn:
        recent_date = conn.exec_driver_sql("SELECT max(start_ts) FROM wynne_activities").scalar()
    epoch = int(recent_date.replace(tzinfo=timezone.utc).timestamp())

    return epoch


def fetch_recent_activities(engine, headers):
    recent_date = get_recent_date(engine)
    response = requests.get(
                "https://www.strava.com/api/v3/athlete/activities",
                headers=headers,
                params={"per_page": 200,
                "after": recent_date},
            )
    response.raise_for_status()
    batch = response.json()

    return pd.json_normalize(batch)


def insert_recent_activities(engine, headers):
    recent_activities = fetch_recent_activities(engine, headers)

    if recent_activities.empty:
        return "No new activities to insert"

    recent_activities["start_lat"] = recent_activities["start_latlng"].str[0]
    recent_activities["start_lng"] = recent_activities["start_latlng"].str[1]

    # land raw batch in staging
    recent_activities.to_sql("recent_activities_raw", engine, if_exists="replace", index=False)

    with engine.begin() as conn:
        conn.exec_driver_sql("""
            INSERT INTO wynne_activities
            SELECT
                id, name, sport_type,
                CAST(start_date_local AS TIMESTAMP),
                ROUND((distance / 1609.344)::numeric, 2),
                ROUND((moving_time / 60.0)::numeric, 2),
                total_elevation_gain,
                CASE WHEN distance > 0
                     THEN ROUND(((moving_time/60.0)/(distance/1609.344))::numeric, 2)
                END,
                "map.summary_polyline",
                start_lat,
                start_lng
            FROM recent_activities_raw
            ON CONFLICT (id) DO NOTHING;
        """)


def run_full_build():
    """One-time: pull ALL activities and (re)build the table. Use to seed a fresh DB."""
    headers = connect_to_strava(credentials)
    all_activities = fetch_activities(headers)
    create_wynne_activities_table(engine, all_activities)
    print(f"Built wynne_activities with {len(all_activities)} activities")


def run_daily_sync():
    """Daily incremental insert — the cron entry point."""
    headers = connect_to_strava(credentials)
    insert_recent_activities(engine, headers)


if __name__ == "__main__":
    import sys

    # `python plugins.py --full`  -> one-time full rebuild (seed a fresh DB)
    # `python plugins.py`         -> daily incremental sync (cron entry point)
    if "--full" in sys.argv:
        run_full_build()
    else:
        run_daily_sync()
