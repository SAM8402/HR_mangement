from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.db.base import Base
from app.core.dependencies import get_db
from app.core.security import hash_password
from app.models.user import User
from app.services.cache_service import cache_service

DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine, monkeypatch) -> AsyncGenerator[AsyncSession, None]:
    connection = await db_engine.connect()
    transaction = await connection.begin()
    session_maker = async_sessionmaker(connection, class_=AsyncSession, expire_on_commit=False)
    
    import app.db.session
    import app.ai.tools
    monkeypatch.setattr(app.db.session, "async_session", session_maker)
    monkeypatch.setattr(app.db.session, "engine", db_engine)
    monkeypatch.setattr(app.ai.tools, "async_session", session_maker)
    
    session = session_maker()

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest_asyncio.fixture(autouse=True)
async def mock_redis(monkeypatch):
    """Mock Redis client in CacheService to prevent actual network calls."""
    class MockRedis:
        def __init__(self):
            self.store = {}
        async def get(self, key):
            return self.store.get(key)
        async def set(self, key, val, ex=None):
            self.store[key] = val
        async def delete(self, *keys):
            for k in keys:
                self.store.pop(k, None)
        async def close(self):
            pass
        def scan_iter(self, match=None):
            import fnmatch
            for k in list(self.store.keys()):
                if match is None or fnmatch.fnmatch(k, match):
                    yield k

    mock_r = MockRedis()
    monkeypatch.setattr(cache_service, "_redis", mock_r)
    monkeypatch.setattr(cache_service, "connect", lambda: asyncio.sleep(0))
    monkeypatch.setattr(cache_service, "disconnect", lambda: asyncio.sleep(0))
    yield mock_r


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Test client overriding the db dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_users(db_session):
    """Seed default users, leave types, and leave balances."""
    from app.models.leave import LeaveType, LeaveBalance
    
    # 1. Seed leave types
    leave_types = {
        "casual": {"days": 18, "carry": False, "max": 5},
        "sick": {"days": 12, "carry": False, "max": 3},
        "earned": {"days": 10, "carry": True, "max": 10},
        "unpaid": {"days": 0, "carry": False, "max": 0},
    }
    lt_objects = {}
    for name, config in leave_types.items():
        lt = LeaveType(
            name=name,
            days_per_year=config["days"],
            carry_forward=config["carry"],
            max_consecutive_days=config["max"],
        )
        db_session.add(lt)
        lt_objects[name] = lt
    await db_session.flush()

    # 2. Seed departments and users
    from datetime import date
    from app.models.department import Department
    
    dept = Department(name="Engineering")
    db_session.add(dept)
    await db_session.flush()

    users = {}
    roles = ["admin", "manager", "hr", "employee"]
    for role in roles:
        user = User(
            name=role.title(),
            email=f"{role}@test.com",
            password_hash=hash_password("password123"),
            role=role,
            joining_date=date(2026, 1, 1),
            is_active=True,
            department_id=dept.id if role in ["hr", "employee"] else None,
        )
        db_session.add(user)
        users[role] = user
    await db_session.flush()

    # 3. Seed leave balances for all users for 2026
    for user in users.values():
        for name, lt in lt_objects.items():
            if name != "unpaid":
                balance = LeaveBalance(
                    user_id=user.id,
                    leave_type_id=lt.id,
                    year=2026,
                    total_days=leave_types[name]["days"],
                    used_days=0,
                    remaining_days=leave_types[name]["days"],
                )
                db_session.add(balance)
    await db_session.flush()
    return users
