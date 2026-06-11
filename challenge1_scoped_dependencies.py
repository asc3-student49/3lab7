"""
Challenge 1: Scoped Dependencies
Implements singleton, request, and transient dependency scopes
"""

from enum import Enum
from typing import TypeVar, Generic, Callable, Any, Optional
from dataclasses import dataclass, field
import asyncio
import logging

logger = logging.getLogger(__name__)


class DependencyScope(Enum):
    """Dependency lifecycle scopes."""

    SINGLETON = "singleton"  # One instance for entire application
    REQUEST = "request"  # New instance per agent run/request
    TRANSIENT = "transient"  # New instance every time requested


T = TypeVar("T")


@dataclass
class DependencyRegistration(Generic[T]):
    """
    Registration of a dependency with its scope and factory.

    Attributes:
        factory: Function that creates instances
        scope: Lifecycle scope
        singleton_instance: Cached instance for singleton scope
    """

    factory: Callable[[], T]
    scope: DependencyScope
    singleton_instance: Optional[T] = None


class ScopedDependencyContainer:
    """
    Dependency container with scope support.

    Manages dependencies with different lifecycles:
    - Singleton: Created once, reused everywhere
    - Request: Created once per request context
    - Transient: Created fresh every time
    """

    def __init__(self):
        """Initialize container with empty registrations."""
        self._registrations: dict[str, DependencyRegistration] = {}
        self._request_instances: dict[str, Any] = {}
        self._request_id = 0

    def register(
        self,
        name: str,
        factory: Callable,
        scope: DependencyScope = DependencyScope.TRANSIENT,
    ):
        """
        Register a dependency.

        Args:
            name: Dependency name/key
            factory: Function to create instances
            scope: Lifecycle scope
        """
        logger.info(f"Registering '{name}' with scope {scope.value}")
        self._registrations[name] = DependencyRegistration(factory=factory, scope=scope)

    async def resolve(self, name: str) -> Any:
        """
        Resolve a dependency by name.

        Args:
            name: Dependency name

        Returns:
            Dependency instance based on scope

        Raises:
            ValueError: If dependency not registered
        """
        # YOUR CODE HERE

    async def _create_instance(self, factory: Callable) -> Any:
        """
        Create instance from factory.

        Handles both sync and async factories.
        """
        instance = factory()

        # If factory returns coroutine, await it
        if asyncio.iscoroutine(instance):
            instance = await instance

        return instance

    def begin_request(self):
        """
        Begin new request scope.

        Clears request-scoped instances.
        """
        # YOUR CODE HERE

    def end_request(self):
        """End current request scope."""
        self._request_instances.clear()
        logger.debug(f"Ended request scope #{self._request_id}")

    async def dispose(self):
        """
        Dispose all dependencies.

        Calls dispose() method on instances that have it.
        """
        # YOUR CODE HERE

    async def _dispose_instance(self, instance: Any, name: str):
        """Dispose a single instance if it has dispose method."""
        if hasattr(instance, "dispose"):
            logger.debug(f"Disposing '{name}'")
            result = instance.dispose()
            if asyncio.iscoroutine(result):
                await result


# Example usage
class DatabaseService:
    """Example singleton service."""

    _instance_count = 0

    def __init__(self):
        DatabaseService._instance_count += 1
        self.instance_id = DatabaseService._instance_count
        logger.info(f"DatabaseService created (instance #{self.instance_id})")

    async def dispose(self):
        logger.info(f"DatabaseService #{self.instance_id} disposed")


class RequestContext:
    """Example request-scoped service."""

    _instance_count = 0

    def __init__(self):
        RequestContext._instance_count += 1
        self.instance_id = RequestContext._instance_count
        self.data = {}
        logger.info(f"RequestContext created (instance #{self.instance_id})")


class Logger:
    """Example transient service."""

    _instance_count = 0

    def __init__(self):
        Logger._instance_count += 1
        self.instance_id = Logger._instance_count
        logger.info(f"Logger created (instance #{self.instance_id})")


async def example_usage():
    """Demonstrate scoped dependencies."""
    # YOUR CODE HERE
    # [SOLUTION]
    container = ScopedDependencyContainer()

    # Register dependencies with different scopes
    container.register("database", DatabaseService, DependencyScope.SINGLETON)
    container.register("context", RequestContext, DependencyScope.REQUEST)
    container.register("logger", Logger, DependencyScope.TRANSIENT)

    print("\n=== First Request ===")
    container.begin_request()

    # Resolve within first request
    db1 = await container.resolve("database")
    ctx1 = await container.resolve("context")
    log1 = await container.resolve("logger")

    # Resolve again - singleton and request reused, transient new
    db2 = await container.resolve("database")
    ctx2 = await container.resolve("context")
    log2 = await container.resolve("logger")

    print(
        f"Database instances same: {db1.instance_id == db2.instance_id}"
    )  # True (singleton)
    print(
        f"Context instances same: {ctx1.instance_id == ctx2.instance_id}"
    )  # True (request)
    print(
        f"Logger instances same: {log1.instance_id == log2.instance_id}"
    )  # False (transient)

    container.end_request()

    print("\n=== Second Request ===")
    container.begin_request()

    # Resolve in second request
    db3 = await container.resolve("database")
    ctx3 = await container.resolve("context")
    log3 = await container.resolve("logger")

    print(
        f"Database same as request 1: {db3.instance_id == db1.instance_id}"
    )  # True (singleton)
    print(
        f"Context same as request 1: {ctx3.instance_id == ctx1.instance_id}"
    )  # False (new request)
    print(f"Logger instance count: {Logger._instance_count}")  # 3 (all transient)

    container.end_request()

    # Cleanup
    await container.dispose()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    asyncio.run(example_usage())
