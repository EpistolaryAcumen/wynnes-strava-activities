from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
from typing import Optional

app = FastAPI(title='Data Science App')

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session_id: Optional[str] = None):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"session_id": session_id}
        )