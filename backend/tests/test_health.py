"""Smoke test API gốc (không cần dữ liệu nghiệp vụ)."""


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "running"
    assert "app" in body
    assert "version" in body


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
