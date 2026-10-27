"""
AICTE FlowOps — Health Endpoint Tests

Validates that GET /api/v1/health returns the expected shape and values.
"""


def test_health_returns_200(client):
    """Health endpoint must return 200 with a 'healthy' status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_body(client):
    """Health response must include status, environment, version, and timestamp."""
    data = client.get("/api/v1/health").json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_version_format(client):
    """Version must follow semver-like format."""
    data = client.get("/api/v1/health").json()
    parts = data["version"].split(".")
    assert len(parts) == 3
    assert all(p.isdigit() for p in parts)


def test_openapi_schema(client):
    """OpenAPI schema must be generated with correct API title."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "AICTE FlowOps API"
    assert "/api/v1/health" in schema["paths"]


def test_docs_page(client):
    """Swagger UI documentation page must return 200."""
    response = client.get("/docs")
    assert response.status_code == 200
