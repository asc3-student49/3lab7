"""
Dependency Factory
Creates and manages dependency lifecycle
"""

from dependencies import *
from database import DatabasePool
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)


class DependencyFactory:
    """
    Factory for creating dependency instances.

    Manages singleton resources (like database pools) and creates
    dependency containers for agent runs.
    """

    def __init__(self):
        """Initialize factory with no active resources."""
        self.db_pool: Optional[DatabasePool] = None
        self._initialized = False

    async def create_dependencies(self) -> AgentDependencies:
        """
        Create fully configured dependency container.

        Initializes singleton resources on first call and reuses them
        for subsequent calls. Creates new instances for request-scoped
        resources.

        Returns:
            AgentDependencies container with all resources
        """
        # Initialize database pool (singleton) on first call
        if not self.db_pool:
            logger.info("Initializing database pool")
            self.db_pool = DatabasePool(
                connection_string=os.getenv("DATABASE_URL", "sqlite:///:memory:"),
                pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            )
            await self.db_pool.initialize()

        # Get connection from pool
        # In production, use pool.get_connection() context manager
        # For now, just use first connection
        database_conn = self.db_pool.connections[0]

        # Create cache client (could be singleton or request-scoped)
        cache = CacheClient(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            ttl=int(os.getenv("CACHE_TTL", "3600")),
        )

        # Create email service (singleton or request-scoped)
        email = EmailService(
            api_key=os.getenv("EMAIL_API_KEY", "test_key"),
            from_address=os.getenv("EMAIL_FROM", "noreply@example.com"),
        )

        # Create configuration (singleton)
        config = AppConfig(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "true").lower() == "true",
            max_retries=int(os.getenv("MAX_RETRIES", "3")),
            timeout=float(os.getenv("TIMEOUT", "30.0")),
            feature_flags={
                "email_notifications": os.getenv("FEATURE_EMAIL", "true").lower()
                == "true",
                "advanced_search": os.getenv("FEATURE_ADVANCED_SEARCH", "false").lower()
                == "true",
                "caching": os.getenv("FEATURE_CACHING", "true").lower() == "true",
            },
        )

        # Create dependency container
        deps = AgentDependencies(
            database=database_conn, cache=cache, email=email, config=config
        )

        self._initialized = True
        logger.info("Dependencies created successfully")

        return deps

    async def shutdown(self):
        """
        Cleanup all resources.

        Closes database pool and releases resources.
        """
        logger.info("Shutting down dependency factory")

        if self.db_pool:
            await self.db_pool.shutdown()
            self.db_pool = None

        self._initialized = False
        logger.info("Dependency factory shutdown complete")

    def is_initialized(self) -> bool:
        """Check if factory has been initialized."""
        return self._initialized


# Example usage
async def main():
    """Example of using dependency factory."""
    from agent import process_order_query

    factory = DependencyFactory()

    try:
        # Create dependencies
        deps = await factory.create_dependencies()

        # Log configuration
        logger.info(f"Environment: {deps.config.environment}")
        logger.info(f"Debug: {deps.config.debug}")
        logger.info(f"Feature flags: {deps.config.feature_flags}")

        # Use agent with dependencies
        response = await process_order_query(
            "What's the status of order ORD-12345?", deps
        )

        print(f"\nResponse: {response}\n")

        # Example: Multiple queries with same dependencies
        queries = [
            "Can you send an update about order ORD-12345?",
            "Is email_notifications enabled?",
        ]

        for query in queries:
            print(f"Query: {query}")
            response = await process_order_query(query, deps)
            print(f"Response: {response}\n")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

    finally:
        # Cleanup resources
        await factory.shutdown()


if __name__ == "__main__":
    import asyncio
    import logging

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
