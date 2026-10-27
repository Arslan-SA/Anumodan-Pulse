"""
AICTE FlowOps — Shared Test Fixtures

Provides a ``client`` fixture backed by FastAPI's TestClient so every
test file can simply inject it.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Yield a TestClient bound to the AICTE FlowOps API."""
    with TestClient(app) as c:
        yield c
