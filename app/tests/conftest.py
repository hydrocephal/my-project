import asyncio
import sys
from unittest.mock import patch

import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.redis import redis_client
from app.db.database import Base, SessionLocal, get_db
from app.main import app
from app.services import chat as chat_service

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TestSettings(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(env_file=".env.test")


test_settings = TestSettings()

test_engine = create_async_engine(test_settings.DATABASE_URL, poolclass=NullPool)

TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def mock_redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("app.services.chat.redis_client", fake), patch("app.core.redis.redis_client", fake):
        yield


@pytest.fixture
def sync_client():
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    async def create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def clear_redis():
        await redis_client.delete("online_users")

    asyncio.get_event_loop().run_until_complete(create_tables())
    chat_service.SessionLocal = TestSessionLocal
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    chat_service.SessionLocal = SessionLocal
    app.dependency_overrides.clear()
    asyncio.get_event_loop().run_until_complete(drop_tables())


@pytest_asyncio.fixture(scope="function")
async def db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
