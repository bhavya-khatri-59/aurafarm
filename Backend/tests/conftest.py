import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.db import create_tables, dispose_engine, init_engine
from app.main import app


@pytest.fixture(autouse=True)
def settings(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret")
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("WEATHER_API_KEY", "")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture
async def db(settings):
    init_engine(f"sqlite+aiosqlite:///{settings.db_path}")
    await create_tables()
    yield
    await dispose_engine()


@pytest.fixture
async def client(db):
    app.state.graph = None
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register(client: AsyncClient, email: str = "farmer@example.com") -> dict:
    response = await client.post(
        "/auth/register", json={"email": email, "name": "Farmer", "password": "correct-horse"}
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
