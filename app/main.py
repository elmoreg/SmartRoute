"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Template

from app.config import get_settings
from app.database import init_db
from app.routers import addresses, routes
from app.services.google_client import close_client

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
INDEX_TEMPLATE = STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    await close_client()


app = FastAPI(title="SmartRoute", lifespan=lifespan)

app.include_router(addresses.router)
app.include_router(routes.router)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    settings = get_settings()
    template = Template(INDEX_TEMPLATE.read_text(encoding="utf-8"))
    return HTMLResponse(template.render(google_maps_api_key=settings.google_maps_api_key))


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
