"""API tests for PatentAI."""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_health_check(client: AsyncClient):
    """Test health endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.anyio
async def test_root(client: AsyncClient):
    """Test root endpoint."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "PatentAI"


@pytest.mark.anyio
async def test_create_patent(client: AsyncClient):
    """Test patent creation."""
    patent_data = {
        "title": "Test Patent for AI System",
        "abstract": "A novel method for testing AI patent systems using automated tools.",
        "claims": "1. A method for testing patent systems.",
        "patent_number": "TEST-001",
        "applicant": "Test Corp"
    }
    
    response = await client.post("/patents/", json=patent_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == patent_data["title"]
    assert "id" in data


@pytest.mark.anyio
async def test_list_patents(client: AsyncClient):
    """Test listing patents."""
    response = await client.get("/patents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.anyio
async def test_search_patents(client: AsyncClient):
    """Test patent search."""
    search_data = {
        "query": "artificial intelligence",
        "limit": 10,
        "search_type": "hybrid"
    }
    
    response = await client.post("/patents/search", json=search_data)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
