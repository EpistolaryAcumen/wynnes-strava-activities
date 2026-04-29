import os
import pandas as pd
import duckdb
import requests
from datetime import datetime, timedelta, timezone
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


def fetch_recent_activities(headers, lookback_days=1):
    now = datetime.now(timezone.utc)
    after = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=lookback_days)

    response = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers=headers,
        params={
            "after": int(after.timestamp()),
            "before": int(now.timestamp()),
            "per_page": 200,
        },
    )
    response.raise_for_status()
    return pd.json_normalize(response.json())


def generate_recent_activities_df(lookback_days=1):
    headers = connect_to_strava(credentials)
    return fetch_recent_activities(headers, lookback_days=lookback_days)


def insert_recent_activities():

    input_df = generate_recent_activities_df()

    if input_df.empty:
        print("No new activities to insert.")
        return
    
    DB_PATH = "wynne_strava.db"
    conn = duckdb.connect(DB_PATH)

    # Filter out IDs that already exist
    existing_ids = conn.sql("SELECT id FROM wynne_activities").fetchdf()["id"]
    input_df = input_df[~input_df["id"].isin(existing_ids)]
    
    cols = ", ".join(ACTIVITY_COLUMNS)
    conn.sql(f"INSERT INTO wynne_activities BY NAME SELECT {cols} FROM input_df")
    conn.close()


if __name__ == "__main__":
    headers = connect_to_strava(credentials)
    recent_activities_df = generate_recent_activities_df()
    insert_recent_activities()
