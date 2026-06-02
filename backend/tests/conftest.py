"""
Cấu hình test: dùng SQLite file tạm để không ghi đè medai.db và tránh lỗi makedirs với :memory:.
"""
from __future__ import annotations

import os
import tempfile

import pytest

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = (
    "sqlite:///" + os.path.abspath(_tmp.name).replace(os.sep, "/")
)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from main import app

    with TestClient(app) as c:
        yield c


def pytest_sessionfinish(session, exitstatus):
    try:
        os.unlink(_tmp.name)
    except OSError:
        pass
