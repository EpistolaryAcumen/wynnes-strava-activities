from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from charts import pace_over_time_chart, cumulative_distance_chart
from statistics import top_five_paces, half_marathon_count, five_k_count, total_distance

load_dotenv()

app = FastAPI(title="Wynne's Strava Data")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = None):
    pace_fig = pace_over_time_chart()
    cumulative_fig = cumulative_distance_chart()
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "session_id": session_id,
            "chart": pace_fig.to_html(full_html=False, include_plotlyjs="cdn"),
            "cumulative_chart": cumulative_fig.to_html(full_html=False, include_plotlyjs=False),
            "top_five": top_five_paces(),
            "half_marathons": half_marathon_count(),
            "five_ks": five_k_count(),
            "total_miles": total_distance(),
        },
    )


@app.get("/behind-the-design", response_class=HTMLResponse)
async def behind_the_design(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="behind-the-design.html",
    )
