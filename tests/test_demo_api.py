"""Integration checks for the API. Set KRIO_TEST_DATABASE_URL to a disposable DB."""

import os
import socket
import threading
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
import jwt
import psycopg2
import pytest
import uvicorn
import yaml
from fastapi.testclient import TestClient

from scripts.seed import seed, seed_id
from services.api.main import app, scan_once
from services.emulator.device_keys import device_key
from services.emulator.fleet import Simulation, build_fleet
from services.emulator.payload import DeviceConfig, build_payload
from services.emulator.sinks import HttpSink

JWT_SECRET = "test-jwt-secret-long-enough-for-demo-api"
DEVICE_SECRET = "test-device-secret-long-enough-for-demo-api"


def test_checked_in_openapi_matches_the_application():
    with open("docs/openapi.yaml", encoding="utf-8") as document:
        assert yaml.safe_load(document) == app.openapi()


@pytest.fixture(scope="module")
def database():
    dsn = os.getenv("KRIO_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Set KRIO_TEST_DATABASE_URL to a migrated, empty test database")
    with pytest.MonkeyPatch.context() as env:
        for key, value in (
            ("DATABASE_URL", dsn),
            ("JWT_SECRET_KEY", JWT_SECRET),
            ("KRIO_DEVICE_SECRET", DEVICE_SECRET),
        ):
            env.setenv(key, value)

        conn = psycopg2.connect(dsn)
        try:
            with conn, conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM tenants")
                if cur.fetchone()[0]:
                    pytest.fail("Integration tests require an empty database")
            seed(conn, "password123")
            seed(conn, "password123")
            with conn, conn.cursor() as cur:
                cur.execute("INSERT INTO tenants (name) VALUES ('Other tenant') RETURNING id")
                tenant_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO users (tenant_id, email, password_hash, role) "
                    "VALUES (%s, 'other@test.local', %s, 'owner')",
                    (tenant_id, bcrypt.hashpw(b"password123", bcrypt.gensalt()).decode()),
                )
            yield conn
        finally:
            conn.close()


@pytest.fixture
def client(database):
    with TestClient(app) as client:
        yield client


def login(client, email="admin@demo.com", password="password123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def headers(client, email="admin@demo.com"):
    response = login(client, email)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def device_headers(code):
    return {"X-Device-Key": device_key(DEVICE_SECRET, code)}


def test_health_auth_and_tenant_isolation(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/auth/me").status_code == 401
    assert login(client, password="invalid").status_code == 401
    auth = headers(client)
    assert client.get("/api/auth/me", headers=auth).json()["role"] == "owner"

    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": seed_id("admin"), "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        JWT_SECRET, algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401

    devices = client.get("/api/devices", headers=auth).json()
    assert len(devices) == 3
    assert all(device["temp_c"] is not None for device in devices)
    other = headers(client, "other@test.local")
    assert client.get("/api/devices", headers=other).json() == []
    assert client.get(f"/api/devices/{devices[0]['id']}", headers=other).status_code == 404
    assert client.get("/api/readings", params={"device_id": devices[0]["id"]}, headers=other).status_code == 404
    assert client.get("/api/alerts", headers=other).json() == []
    assert client.get("/api/shipments", headers=other).json() == []


def test_ingest_validation_idempotency_and_watermark(client, database):
    code = "KRIO-0002"
    now = datetime.now(timezone.utc)
    payload = build_payload(DeviceConfig(code), now, 1, 3.25, batt_v=4.1)
    auth = device_headers(code)
    assert client.post("/api/ingest", json=payload).status_code == 401
    assert client.post("/api/ingest", json=payload, headers=device_headers("KRIO-0001")).status_code == 401
    for invalid in (
        dict(payload, schema="invalid"), dict(payload, seq="1"), dict(payload, ts=123456789),
        dict(payload, link="lora"), dict(payload, padded="x" * 512),
        {key: value for key, value in payload.items() if key != "buffered"},
    ):
        assert client.post("/api/ingest", json=invalid, headers=auth).status_code == 400

    unknown = dict(payload, device_id="UNKNOWN")
    assert client.post("/api/ingest", json=unknown, headers=device_headers("UNKNOWN")).status_code == 404
    assert client.post("/api/ingest", json=payload, headers=auth).status_code == 201
    duplicate = client.post("/api/ingest", json=dict(payload, temp_c=9), headers=auth)
    assert duplicate.status_code == 200
    assert duplicate.json() == {"inserted": False}

    old = build_payload(DeviceConfig(code), now - timedelta(minutes=2), 0, 4.5, buffered=True)
    assert client.post("/api/ingest", json=old, headers=auth).status_code == 201
    with database, database.cursor() as cur:
        cur.execute(
            "SELECT d.last_seen_at = r.ts, r.temp_c FROM devices d JOIN readings r ON r.device_id=d.id "
            "WHERE d.device_id=%s AND r.ts=%s",
            (code, payload["ts"]),
        )
        assert cur.fetchall() == [(True, 3.25)]


def test_shipment_readings_and_alerts(client, database):
    auth = headers(client)
    listing = client.get("/api/shipments", headers=auth).json()
    assert len(listing) == 3
    shipment = next(item for item in listing if item["device_id"] == seed_id("KRIO-0001"))
    assert shipment["temp_max_c"] == 4
    assert client.get(f"/api/shipments/{shipment['id']}", headers=auth).json() == shipment
    end = datetime.now(timezone.utc)
    for hours in (1, 24):
        chart = client.get(
            "/api/readings",
            params={"device_id": shipment["device_id"], "from": (end - timedelta(hours=hours)).isoformat(),
                    "to": end.isoformat(), "bucket": "5m"},
            headers=auth,
        )
        assert chart.status_code == 200
        assert len(chart.json()) >= hours * 11

    baseline = client.get("/api/alerts", headers=auth).json()
    assert len(baseline) == 2
    code = "KRIO-0001"
    payload = build_payload(DeviceConfig(code), end, 1, 12)
    assert client.post("/api/ingest", json=payload, headers=device_headers(code)).status_code == 201
    scan_once()
    scan_once()
    active = client.get("/api/alerts", headers=auth).json()
    assert len(active) == len(baseline) + 1
    alert = active[0]
    assert alert["kind"] == "KEGAGALAN_PENDINGIN"
    assert alert["severity"] == "critical"
    ack_url = f"/api/alerts/{alert['id']}/ack"
    assert client.post(ack_url, headers=headers(client, "viewer@demo.com")).status_code == 403
    assert client.post(ack_url, headers=headers(client, "other@test.local")).status_code == 404
    ack = client.post(ack_url, headers=auth).json()
    assert ack["acked_by"] == seed_id("admin")
    assert ack["resolved_at"] is not None
    assert client.post(ack_url, headers=auth).json() == ack
    assert alert["id"] not in {item["id"] for item in client.get("/api/alerts", headers=auth).json()}

    with database, database.cursor() as cur:
        cur.execute(
            "UPDATE readings SET ts = ts - interval '3 days' WHERE device_id = %s",
            (shipment["device_id"],),
        )
        cur.execute(
            "UPDATE devices SET last_seen_at = last_seen_at - interval '3 days' WHERE id = %s",
            (shipment["device_id"],),
        )
    scan_once()
    offline = client.get("/api/alerts", headers=auth).json()[0]
    assert offline["kind"] == "DEVICE_OFFLINE"
    detail_url = f"/api/devices/{shipment['device_id']}"
    assert client.get(detail_url, headers=auth).json()["status"] == "offline"
    recovered_at = datetime.now(timezone.utc) + timedelta(seconds=1)
    recovery = build_payload(DeviceConfig(code), recovered_at, 2, 2)
    assert client.post("/api/ingest", json=recovery, headers=device_headers(code)).status_code == 201
    scan_once()
    resolved = client.get("/api/alerts", headers=auth, params={"status": "resolved"}).json()
    assert offline["id"] in {item["id"] for item in resolved}
    assert client.get(detail_url, headers=auth).json()["status"] == "online"


def test_emulator_http_to_postgres_to_devices(database):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 5
            while not server.started and thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert server.started
            with httpx.Client(base_url=f"http://127.0.0.1:{port}") as client:
                auth = headers(client)
                sink = HttpSink(f"http://127.0.0.1:{port}/api/ingest", DEVICE_SECRET)
                now = datetime.now(timezone.utc) + timedelta(seconds=2)
                devices = build_fleet([("KRIO-0003", "lora")], mode="normal", seed=42)
                Simulation(devices, sink, duration_s=0, started_at=now).run()
                data = client.get("/api/devices", headers=auth).json()
                lora = next(item for item in data if item["device_id"] == "KRIO-0003")
                assert lora["status"] == "online"
                with database, database.cursor() as cur:
                    cur.execute(
                        "SELECT temp_c FROM readings WHERE device_id = %s AND ts = %s",
                        (lora["id"], lora["last_seen_at"]),
                    )
                    assert cur.fetchone()[0] == pytest.approx(lora["temp_c"])
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            assert not thread.is_alive()


class ClientSink:
    """Send emulator payloads through the in-process API, like HttpSink does."""

    def __init__(self, client):
        self.client = client

    def send(self, payload):
        response = self.client.post("/api/ingest", json=payload, headers=device_headers(payload["device_id"]))
        assert response.status_code in (200, 201), response.text

    def close(self):
        pass


def test_simulation_runs_scenario_through_ingest(client, database, monkeypatch):
    from services.api import simulation

    monkeypatch.setattr(simulation, "SPEED", 7200.0)
    monkeypatch.setattr(simulation, "make_sink", lambda: ClientSink(client))
    auth = headers(client)
    device = next(d for d in client.get("/api/devices", headers=auth).json() if d["device_id"] == "KRIO-0002")
    form = {"device_id": device["id"], "mode": "excursion"}

    viewer = headers(client, "viewer@demo.com")
    assert client.post("/api/simulation", json=form, headers=viewer).status_code == 403
    other = headers(client, "other@test.local")
    assert client.post("/api/simulation", json=form, headers=other).status_code == 404

    started = client.post("/api/simulation", json=form, headers=auth)
    assert started.status_code == 201
    assert client.post("/api/simulation", json=form, headers=auth).status_code == 409
    for _ in range(200):
        state = client.get("/api/simulation", headers=auth).json()
        if state["state"] != "running":
            break
        time.sleep(0.05)
    assert state["state"] == "finished", state
    assert state["sent"] > 0
    assert [e["text"] for e in state["events"]][:2] == ["Simulasi dimulai", "Pendingin berhenti bekerja"]
    assert client.get("/api/simulation", headers=other).json() is None

    scan_once()
    active = client.get("/api/alerts", headers=auth).json()
    assert any(a["device_id"] == device["id"] and a["kind"] == "KEGAGALAN_PENDINGIN" for a in active)


def test_simulated_time_scales_offline_threshold():
    from services.alerting.rules import evaluate_offline

    now = datetime.now(timezone.utc)
    seen = now - timedelta(seconds=31)
    assert evaluate_offline(seen, now, "Boks", link_type="cellular") is None
    draft = evaluate_offline(seen, now, "Boks", link_type="cellular", time_scale=20)
    assert draft is not None and "waktu simulasi" in draft.message
    assert evaluate_offline(seen, now, "Boks", link_type="lora", time_scale=20) is None
