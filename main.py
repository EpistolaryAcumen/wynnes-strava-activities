import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional

from strava_wynne_activities import get_athlete

load_dotenv()

app = FastAPI(title='Data Science App')

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

STRAVA_CREDENTIALS = {
    "client_id": os.environ["STRAVA_CLIENT_ID"],
    "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
    "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = None):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"session_id": session_id},
    )


@app.get("/wynne-activities", response_class=HTMLResponse)
async def wynne_activities(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="wynne-activities.html",
    )


@app.get("/wynne-activities/chart", response_class=HTMLResponse)
async def wynne_activities_chart(request: Request):
    athlete = get_athlete(STRAVA_CREDENTIALS)
    fig = athlete.pace_over_time_chart()
    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    return templates.TemplateResponse(
        request=request,
        name="wynne-activities-chart.html",
        context={"chart": chart_html},
    )