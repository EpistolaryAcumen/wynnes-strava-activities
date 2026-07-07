import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Optional

from charts import pace_over_time_chart
from top_five import top_five_paces

load_dotenv()

app = FastAPI(title="Wynne's Strava Data")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = None):
    fig = pace_over_time_chart()
    chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "session_id": session_id,
            "chart": chart_html,
            "top_five": top_five_paces(),
        },
    )


@app.get("/behind-the-design", response_class=HTMLResponse)
async def behind_the_design(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="behind-the-design.html",
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
