"""Run once to build the DuckDB database and load the wynne_activities table."""

import os
import duckdb
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

credentials = {
    "client_id": os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
}

DB_PATH = "wynne_strava.db"

ACTIVITY_COLUMNS = [
    "id", "name", "sport_type",
    "distance", "elapsed_time", "total_elevation_gain",
    "start_date_local", "achievement_count", "kudos_count",
    "average_speed", "max_speed", "pr_count",
]


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
    """Fetch athlete activities from Strava and return as a DataFrame."""
    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers,
        params={"per_page": 200, "page": 1},
    )
    response.raise_for_status()
    return pd.json_normalize(response.json())


def create_database(db_path):
    """Create (or open) the DuckDB database and return the connection."""
    conn = duckdb.connect(db_path)
    return conn


def create_wynne_activities_table(conn, activities_df):
    """Create the wynne_activities table from a DataFrame of Strava activities."""
    cols = ", ".join(ACTIVITY_COLUMNS)
    conn.sql(f"CREATE TABLE IF NOT EXISTS wynne_activities AS SELECT {cols} FROM activities_df")


if __name__ == "__main__":
    headers = connect_to_strava(credentials)
    activities_df = fetch_activities(headers)

    conn = create_database(DB_PATH)
    create_wynne_activities_table(conn, activities_df)
    conn.close()

    print(f"Created {DB_PATH} with {len(activities_df)} rows in wynne_activities.")