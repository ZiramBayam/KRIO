"""FastAPI entry point for the KRIO demo."""

import asyncio
import logging
import os
from contextlib import asynccontextmanager

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.alerting.scanner import scan

from . import auth, dashboard, simulation, telemetry
from .db import transaction

load_dotenv()
logger = logging.getLogger(__name__)


def scan_once():
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_xact_lock(%s)", (847206183,))
            if cur.fetchone()[0]:
                return scan(conn, time_scale=simulation.time_scale)
    finally:
        conn.close()


async def schedule_alerts(stop: asyncio.Event):
    while not stop.is_set():
        try:
            await asyncio.to_thread(scan_once)
        except psycopg2.Error:
            logger.warning("Scheduled alert scan failed", exc_info=False)
        try:
            # Scan faster while a dashboard simulation compresses time.
            await asyncio.wait_for(stop.wait(), timeout=5 if simulation.any_running() else 30)
        except TimeoutError:
            continue


@asynccontextmanager
async def lifespan(app: FastAPI):
    for name in ("JWT_SECRET_KEY", "KRIO_DEVICE_SECRET"):
        value = os.getenv(name, "")
        if len(value.encode()) < 32 or value.startswith(("change-me-", "replace-with-")):
            raise RuntimeError(f"{name} must be a generated secret of at least 32 bytes")
    if not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required")
    stop = asyncio.Event()
    task = asyncio.create_task(schedule_alerts(stop))
    try:
        yield
    finally:
        stop.set()
        await task


app = FastAPI(title="KRIO Demo API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("KRIO_CORS_ORIGINS", "http://localhost:3000").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Device-Key"],
)


@app.exception_handler(psycopg2.OperationalError)
def database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": "Database unavailable"})


class Health(BaseModel):
    status: str


@app.get("/api/health", response_model=Health, responses={503: {"model": Health}})
def health():
    try:
        with transaction() as cur:
            cur.execute("SELECT 1")
    except psycopg2.Error:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")


def openapi():
    if app.openapi_schema is None:
        document = default_openapi()
        schema = telemetry.Telemetry.model_json_schema(ref_template="#/components/schemas/{model}")
        components = document.setdefault("components", {}).setdefault("schemas", {})
        components.update(schema.pop("$defs", {}))
        components["Telemetry"] = schema
    return app.openapi_schema


default_openapi = app.openapi
app.openapi = openapi
