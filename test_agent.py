"""
Agent Tests with Mocked Dependencies
Demonstrates testing agents using dependency injection
"""

import pytest
from unittest.mock import AsyncMock, Mock
from dependencies import *
from agent import order_agent, get_order, send_order_update, check_feature_enabled
from pydantic_ai import RunContext
from pydantic_ai.models.test import TestModel
from pydantic_ai.usage import RunUsage


class MockDatabase:
    """Mock database for testing."""

    def __init__(self):
        self.query = AsyncMock(
            return_value=[
                {
                    "id": "ORD-123",
                    "status": "shipped",
                    "customer_email": "test@example.com",
                    "total": 99.99,
                    "created_at": "2026-04-01T10:00:00Z",
                }
            ]
        )
        self.execute = AsyncMock(return_value=1)
        self.close = AsyncMock()


class MockCache:
    """Mock cache for testing."""

    def __init__(self):
        self.storage = {}
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)
        self.delete = AsyncMock(side_effect=self._delete)
        self.clear = AsyncMock(side_effect=self._clear)
        self.exists = AsyncMock(side_effect=self._exists)

    async def _get(self, key):
        return self.storage.get(key)

    async def _set(self, key, value, ttl=None):
        self.storage[key] = value

    async def _delete(self, key):
        if key in self.storage:
            del self.storage[key]

    async def _clear(self):
        self.storage.clear()

    async def _exists(self, key):
        return key in self.storage


class MockEmail:
    """Mock email service for testing."""

    def __init__(self):
        self.send = AsyncMock(return_value=True)
        self.send_template = AsyncMock(return_value=True)
        self.sent_emails = []

        # Make send track emails
        async def track_send(to, subject, body, html=False):
            self.sent_emails.append(
                {"to": to, "subject": subject, "body": body, "html": html}
            )
            return True

        self.send.side_effect = track_send


def create_test_dependencies(**overrides) -> AgentDependencies:
    """
    Create mock dependencies for testing.

    Args:
        **overrides: Override specific dependencies

    Returns:
        AgentDependencies with mocked components
    """
    return AgentDependencies(
        database=overrides.get("database", MockDatabase()),
        cache=overrides.get("cache", MockCache()),
        email=overrides.get("email", MockEmail()),
        config=overrides.get(
            "config",
            AppConfig(
                environment="test",
                debug=True,
                max_retries=1,
                timeout=5.0,
                feature_flags={"email_notifications": True, "advanced_search": False},
            ),
        ),
    )


def create_run_context(deps: AgentDependencies) -> RunContext[AgentDependencies]:
    """
    Create RunContext for testing.

    pydantic-ai 1.x requires `deps`, `model`, and `usage` keyword args.
    Earlier versions accepted `model_name` as a string and supplied
    defaults for `usage`; both shapes are gone in 1.87+. The minimal
    valid construction is shown here.

    Args:
        deps: Dependencies to inject

    Returns:
        RunContext instance suitable for unit-testing tool functions.
    """
    return RunContext(deps=deps, model=TestModel(), usage=RunUsage())


@pytest.mark.asyncio
async def test_get_order_cache_miss():
    """Test order lookup with cache miss."""
    deps = create_test_dependencies()
    ctx = create_run_context(deps)

    # Should query database and cache result
    order = await get_order(ctx, "ORD-123")

    assert order.order_id == "ORD-123"
    assert order.status == "shipped"
    assert order.customer_email == "test@example.com"
    assert order.total == 99.99

    # Verify database was queried
    deps.database.query.assert_called_once()

    # Verify result was cached
    deps.cache.set.assert_called_once()
    call_args = deps.cache.set.call_args
    assert call_args[0][0] == "order:ORD-123"


@pytest.mark.asyncio
async def test_get_order_cache_hit():
    """Test order lookup with cache hit."""
    deps = create_test_dependencies()

    # Pre-populate cache
    await deps.cache.set(
        "order:ORD-456",
        {
            "order_id": "ORD-456",
            "status": "delivered",
            "customer_email": "cached@example.com",
            "total": 49.99,
            "created_at": "2026-04-05T10:00:00Z",
        },
    )

    ctx = create_run_context(deps)

    # Should use cached value
    order = await get_order(ctx, "ORD-456")

    assert order.order_id == "ORD-456"
    assert order.status == "delivered"
    assert order.customer_email == "cached@example.com"

    # Verify database was NOT queried
    deps.database.query.assert_not_called()


@pytest.mark.asyncio
async def test_send_order_update():
    """Test sending order update email."""
    deps = create_test_dependencies()
    ctx = create_run_context(deps)

    # Pre-populate cache with order
    await deps.cache.set(
        "order:ORD-789",
        {
            "order_id": "ORD-789",
            "status": "processing",
            "customer_email": "recipient@example.com",
            "total": 149.99,
            "created_at": "2026-04-10T10:00:00Z",
        },
    )

    # Send update
    success = await send_order_update(ctx, "ORD-789", "Your order will arrive tomorrow")

    assert success is True

    # Verify email was sent
    deps.email.send.assert_called_once()

    # Check email details
    assert len(deps.email.sent_emails) == 1
    sent = deps.email.sent_emails[0]
    assert sent["to"] == "recipient@example.com"
    assert "ORD-789" in sent["subject"]
    assert "arrive tomorrow" in sent["body"]


@pytest.mark.asyncio
async def test_send_order_update_feature_disabled():
    """Test email not sent when feature is disabled."""
    # Create config with email disabled
    config = AppConfig(
        environment="test",
        debug=True,
        max_retries=1,
        timeout=5.0,
        feature_flags={"email_notifications": False},
    )

    deps = create_test_dependencies(config=config)
    ctx = create_run_context(deps)

    # Pre-populate cache
    await deps.cache.set(
        "order:ORD-999",
        {
            "order_id": "ORD-999",
            "status": "shipped",
            "customer_email": "test@example.com",
            "total": 99.99,
            "created_at": "2026-04-10T10:00:00Z",
        },
    )

    # Try to send update
    success = await send_order_update(ctx, "ORD-999", "Test message")

    # Should return False (feature disabled)
    assert success is False

    # Email should not be sent
    deps.email.send.assert_not_called()


@pytest.mark.asyncio
async def test_check_feature_enabled():
    """Test checking feature flags."""
    deps = create_test_dependencies()
    ctx = create_run_context(deps)

    # Check enabled feature
    enabled = await check_feature_enabled(ctx, "email_notifications")
    assert enabled is True

    # Check disabled feature
    disabled = await check_feature_enabled(ctx, "advanced_search")
    assert disabled is False

    # Check non-existent feature (should default to False)
    missing = await check_feature_enabled(ctx, "nonexistent_feature")
    assert missing is False


@pytest.mark.asyncio
async def test_dependency_isolation():
    """Test that each agent run gets isolated dependencies."""
    deps1 = create_test_dependencies()
    deps2 = create_test_dependencies()

    # Modify one dependency's cache
    await deps1.cache.set("key", "value1")
    await deps2.cache.set("key", "value2")

    # Verify isolation - each has its own cache
    val1 = await deps1.cache.get("key")
    val2 = await deps2.cache.get("key")

    assert val1 == "value1"
    assert val2 == "value2"
    assert val1 != val2


@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test multiple concurrent agent runs with independent dependencies."""
    import asyncio

    async def process_order(order_id: str):
        deps = create_test_dependencies()
        ctx = create_run_context(deps)
        return await get_order(ctx, order_id)

    # Run multiple concurrent requests
    results = await asyncio.gather(
        process_order("ORD-1"), process_order("ORD-2"), process_order("ORD-3")
    )

    # All should succeed
    assert len(results) == 3
    for result in results:
        assert result.status == "shipped"


@pytest.mark.asyncio
async def test_order_not_found():
    """Test handling of non-existent order."""
    # Create mock that returns empty result
    mock_db = MockDatabase()
    mock_db.query = AsyncMock(return_value=[])

    deps = create_test_dependencies(database=mock_db)
    ctx = create_run_context(deps)

    # Should raise ValueError
    with pytest.raises(ValueError, match="Order ORD-NONE not found"):
        await get_order(ctx, "ORD-NONE")


@pytest.mark.asyncio
async def test_database_error_handling():
    """Test handling of database errors."""
    # Create mock that raises exception
    mock_db = MockDatabase()
    mock_db.query = AsyncMock(side_effect=Exception("Database connection failed"))

    deps = create_test_dependencies(database=mock_db)
    ctx = create_run_context(deps)

    # Should propagate exception
    with pytest.raises(Exception, match="Database connection failed"):
        await get_order(ctx, "ORD-ERROR")


@pytest.mark.asyncio
async def test_cache_operations():
    """Test cache operations work correctly."""
    deps = create_test_dependencies()

    # Test set and get
    await deps.cache.set("test_key", {"data": "value"})
    result = await deps.cache.get("test_key")
    assert result == {"data": "value"}

    # Test exists
    exists = await deps.cache.exists("test_key")
    assert exists is True

    # Test delete
    await deps.cache.delete("test_key")
    result = await deps.cache.get("test_key")
    assert result is None

    # Test clear
    await deps.cache.set("key1", "val1")
    await deps.cache.set("key2", "val2")
    await deps.cache.clear()
    assert await deps.cache.get("key1") is None
    assert await deps.cache.get("key2") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
