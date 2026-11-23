"""Frontend serving: / returns index.html, /static serves assets, and a missing
frontend directory degrades to a clear 503 instead of crashing the backend."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app import create_app


def test_index_and_static_are_served(settings):
    settings.frontend_dir.mkdir(parents=True)
    (settings.frontend_dir / "index.html").write_text(
        "<!doctype html><title>CLAD</title><p id=marker>工作台</p>", encoding="utf-8"
    )
    (settings.frontend_dir / "app.js").write_text("console.log('clad')", encoding="utf-8")

    with TestClient(create_app(settings=settings)) as client:
        index = client.get("/")
        assert index.status_code == 200
        assert "text/html" in index.headers["content-type"]
        assert "工作台" in index.text

        asset = client.get("/static/app.js")
        assert asset.status_code == 200
        assert "console.log" in asset.text

        assert client.get("/static/missing.js").status_code == 404


def test_missing_frontend_directory_returns_503(settings):
    with TestClient(create_app(settings=settings)) as client:
        index = client.get("/")
        assert index.status_code == 503
        assert "CLAD_FRONTEND_DIR" in index.text
        assert client.get("/static/app.js").status_code == 404


def test_health_endpoint(settings):
    with TestClient(create_app(settings=settings)) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
