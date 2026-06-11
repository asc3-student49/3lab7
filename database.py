"""
Database Connection Pool Management
Demonstrates proper resource lifecycle management
"""

from contextlib import asynccontextmanager
from typing import List
from dependencies import DatabaseConnection
import logging

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Manage database connection pool.

    Provides connection pooling for efficient resource usage.
    Ensures proper initialization and cleanup.
    """

    def __init__(self, connection_string: str, pool_size: int = 10):
        """
        Initialize database pool.

        Args:
            connection_string: Database connection string
            pool_size: Number of connections in pool
        """
        self.connection_string = connection_string
        self.pool_size = pool_size
        self.connections: List[DatabaseConnection] = []
        self._initialized = False
        self._in_use = set()

    async def initialize(self):
        """
        Initialize connection pool.

        Creates pool_size connections and makes them available.
        """
        if self._initialized:
            logger.warning("Database pool already initialized")
            return

        logger.info(f"Initializing database pool (size={self.pool_size})")

        for i in range(self.pool_size):
            conn = DatabaseConnection(
                connection_string=self.connection_string, pool_size=self.pool_size
            )
            self.connections.append(conn)
            logger.debug(f"Created connection {i + 1}/{self.pool_size}")

        self._initialized = True
        logger.info("Database pool initialized successfully")

    async def shutdown(self):
        """
        Shutdown connection pool.

        Closes all connections and releases resources.
        """
        if not self._initialized:
            logger.warning("Database pool not initialized, nothing to shutdown")
            return

        logger.info("Shutting down database pool")

        # Close all connections
        for i, conn in enumerate(self.connections):
            await conn.close()
            logger.debug(f"Closed connection {i + 1}/{len(self.connections)}")

        self.connections.clear()
        self._in_use.clear()
        self._initialized = False

        logger.info("Database pool shutdown complete")

    @asynccontextmanager
    async def get_connection(self):
        """
        Get connection from pool (context manager).

        Ensures connection is properly returned to pool after use.

        Usage:
            async with pool.get_connection() as conn:
                result = await conn.query("SELECT * FROM table")

        Yields:
            DatabaseConnection from pool
        """
        if not self._initialized:
            await self.initialize()

        # Get available connection
        # In production, implement proper connection checkout/checkin
        # For now, simple round-robin with first available
        conn = None
        for c in self.connections:
            if c not in self._in_use:
                conn = c
                self._in_use.add(c)
                break

        if not conn:
            # All connections in use - for simplicity, use first one
            # Production would wait for available connection or create new one
            logger.warning("All connections in use, reusing connection")
            conn = self.connections[0]

        try:
            yield conn
        finally:
            # Return connection to pool
            if conn in self._in_use:
                self._in_use.discard(conn)

    def get_stats(self) -> dict:
        """
        Get pool statistics.

        Returns:
            Dictionary with pool stats
        """
        return {
            "pool_size": self.pool_size,
            "connections_created": len(self.connections),
            "connections_in_use": len(self._in_use),
            "connections_available": len(self.connections) - len(self._in_use),
            "initialized": self._initialized,
        }


# Example usage
async def example_usage():
    """Example of using database pool."""
    pool = DatabasePool("sqlite:///:memory:", pool_size=5)

    try:
        # Initialize pool
        await pool.initialize()

        # Use connection from pool
        async with pool.get_connection() as conn:
            results = await conn.query(
                "SELECT * FROM orders WHERE id = :id", {"id": "ORD-123"}
            )
            print(f"Query results: {results}")

        # Check pool stats
        stats = pool.get_stats()
        print(f"Pool stats: {stats}")

    finally:
        # Clean shutdown
        await pool.shutdown()


if __name__ == "__main__":
    import asyncio

    asyncio.run(example_usage())
