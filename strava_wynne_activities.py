import time

import requests
import pandas as pd
import plotly.graph_objects as go

CACHE_TTL = 30 * 60  # 30 minutes in seconds
_cache: dict = {"athlete": None, "expires_at": 0}


def get_athlete(credentials: dict) -> "StravaAthlete":
    """Return a cached StravaAthlete, re-fetching from Strava when the cache expires."""
    now = time.time()
    if _cache["athlete"] and now < _cache["expires_at"]:
        return _cache["athlete"]

    athlete = StravaAthlete(credentials)
    _cache["athlete"] = athlete
    _cache["expires_at"] = now + CACHE_TTL
    return athlete


class StravaAthlete:
    def __init__(self, credentials):
        self.credentials = credentials
        self.headers = self._authenticate()
        self.profile = self._fetch_profile()
        self.activities = self._fetch_activities()

    def _authenticate(self):
        token_response = requests.post(
            "https://www.strava.com/oauth/token",
            data={**self.credentials, "grant_type": "refresh_token"},
        )
        tokens = token_response.json()
        return {"Authorization": f"Bearer {tokens['access_token']}"}

    def _fetch_profile(self):
        return requests.get(
            "https://www.strava.com/api/v3/athlete",
            headers=self.headers,
        ).json()

    def _fetch_activities(self):
        activities = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            headers=self.headers,
            params={"per_page": 200, "page": 1},
        ).json()
        return pd.json_normalize(activities)

    def prep_activities(self):
        df = self.activities[[
            "distance", "elapsed_time", "total_elevation_gain",
            "start_date_local", "achievement_count", "kudos_count",
            "average_speed", "max_speed", "pr_count",
        ]].copy()

        df["miles"] = (df["distance"] / 1609.344).round(2)

        pace_secs = df["elapsed_time"] / df["miles"]
        minutes = (pace_secs // 60).astype(int)
        seconds = (pace_secs % 60).round(0).astype(int)
        df["mile_pace"] = minutes.astype(str) + ":" + seconds.astype(str).str.zfill(2)

        return df

    def pace_over_time_chart(self, min_pace=5, max_pace=15):
        df = self.prep_activities()
        df["start_date_local"] = pd.to_datetime(df["start_date_local"])
        df["pace_minutes"] = (df["elapsed_time"] / 60) / df["miles"]
        df = df.sort_values("start_date_local")

        plot_df = df[(df["pace_minutes"] >= min_pace) & (df["pace_minutes"] <= max_pace)]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=plot_df["start_date_local"],
            y=plot_df["pace_minutes"],
            mode="lines+markers",
            marker=dict(size=6),
            text=[
                f"{self._format_pace(p)} /mi — {d:.2f} mi"
                for p, d in zip(plot_df["pace_minutes"], plot_df["miles"])
            ],
            hovertemplate="%{x|%b %d, %Y}<br>%{text}<extra></extra>",
        ))

        fig.update_layout(
            title="Mile Pace Over Time",
            xaxis_title="Date",
            yaxis_title="Mile Pace",
            yaxis=dict(
                autorange="reversed",
                tickvals=list(range(min_pace, max_pace + 1)),
                ticktext=[self._format_pace(v) for v in range(min_pace, max_pace + 1)],
            ),
            template="plotly_white",
            height=500,
        )

        return fig

    @staticmethod
    def _format_pace(minutes):
        m = int(minutes)
        s = int((minutes % 1) * 60)
        return f"{m}:{s:02d}"
