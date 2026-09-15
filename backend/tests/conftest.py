import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db, get_redis

# Using shared cache in-memory SQLite keeps tables visible across all async sessions
test_engine = create_async_engine(
    "sqlite+aiosqlite:///file:memdb_shared?mode=memory&cache=shared&uri=true",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


class MockRedis:
    """In-memory Redis emulator for isolated unit tests."""
    def __init__(self):
        self.store = {}
        self.ttls = {}

    async def hset(self, key: str, field_or_mapping=None, value=None, mapping=None):
        if key not in self.store:
            self.store[key] = {}
        if mapping is not None:
            for k, v in mapping.items():
                self.store[key][str(k)] = str(v)
        elif isinstance(field_or_mapping, dict):
            for k, v in field_or_mapping.items():
                self.store[key][str(k)] = str(v)
        elif field_or_mapping is not None and value is not None:
            self.store[key][str(field_or_mapping)] = str(value)
        return True

    async def hgetall(self, key: str):
        return self.store.get(key, {})

    async def expire(self, key: str, seconds: int):
        self.ttls[key] = seconds
        return True

    async def ping(self):
        return True

    async def aclose(self):
        pass


mock_redis_instance = MockRedis()


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


async def override_get_redis():
    yield mock_redis_instance


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    mock_redis_instance.store.clear()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
