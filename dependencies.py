"""
Dependency Definitions
Core dependencies for order management agent
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
import logging


@dataclass
class DatabaseConnection:
    """Database connection dependency."""

    connection_string: str
    pool_size: int = 10
    timeout: float = 5.0

    def __post_init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Database connection initialized: {self.connection_string}")

    async def query(self, sql: str, params: Dict[str, Any] = None) -> list:
        """
        Execute database query.

        Args:
            sql: SQL query string
            params: Query parameters

        Returns:
            List of query results
        """
        self.logger.debug(f"Executing query: {sql}")

        # Simulate database query
        # In production, use SQLAlchemy, asyncpg, etc.
        if "orders" in sql.lower():
            order_id = params.get("id", "ORD-123") if params else "ORD-123"
            return [
                {
                    "id": order_id,
                    "status": "shipped",
                    "customer_email": "customer@example.com",
                    "total": 99.99,
                    "created_at": "2026-04-01T10:00:00Z",
                }
            ]

        return []

    async def execute(self, sql: str, params: Dict[str, Any] = None) -> int:
        """
        Execute database command (INSERT, UPDATE, DELETE).

        Returns:
            Number of affected rows
        """
        self.logger.debug(f"Executing command: {sql}")
        return 1

    async def close(self):
        """Close database connection."""
        self.logger.info("Database connection closed")


@dataclass
class CacheClient:
    """Cache layer dependency."""

    host: str
    port: int = 6379
    ttl: int = 3600
    _cache: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Cache client initialized: {self.host}:{self.port}")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        value = self._cache.get(key)
        self.logger.debug(f"Cache {'HIT' if value else 'MISS'}: {key}")
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (uses default if not specified)
        """
        self._cache[key] = value
        self.logger.debug(f"Cache SET: {key} (ttl={ttl or self.ttl})")

    async def delete(self, key: str):
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]
            self.logger.debug(f"Cache DELETE: {key}")

    async def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        self.logger.info("Cache cleared")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return key in self._cache


@dataclass
class EmailService:
    """Email notification service."""

    api_key: str
    from_address: str

    def __post_init__(self):
        self.logger = logging.getLogger(__name__)
        self.sent_emails = []  # Track sent emails for testing

    async def send(self, to: str, subject: str, body: str, html: bool = False) -> bool:
        """
        Send email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        self.logger.info(f"Sending email to {to}: {subject}")

        # Track for testing
        self.sent_emails.append(
            {"to": to, "subject": subject, "body": body, "html": html}
        )

        # Simulate email sending
        # In production, use SendGrid, AWS SES, etc.
        return True

    async def send_template(
        self, to: str, template: str, variables: Dict[str, Any]
    ) -> bool:
        """
        Send email using template.

        Args:
            to: Recipient email
            template: Template name
            variables: Template variables

        Returns:
            True if sent successfully
        """
        self.logger.info(f"Sending template '{template}' to {to}")

        # Simple template rendering
        subject = f"Order Update - {variables.get('order_id', 'N/A')}"
        body = f"Template: {template}\nVariables: {variables}"

        return await self.send(to, subject, body)


@dataclass
class AppConfig:
    """Application configuration."""

    environment: str
    debug: bool
    max_retries: int
    timeout: float
    feature_flags: Dict[str, bool]

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment.lower() == "development"

    def get_feature(self, feature: str, default: bool = False) -> bool:
        """
        Get feature flag value.

        Args:
            feature: Feature name
            default: Default value if not found

        Returns:
            Feature flag value
        """
        return self.feature_flags.get(feature, default)


@dataclass
class AgentDependencies:
    """
    Container for all agent dependencies.

    Provides type-safe dependency injection to agent tools.
    """

    database: DatabaseConnection
    cache: CacheClient
    email: EmailService
    config: AppConfig

    async def cleanup(self):
        """Cleanup all dependencies."""
        await self.database.close()
        await self.cache.clear()
