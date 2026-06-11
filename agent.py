"""
Order Management Agent with Dependency Injection
Demonstrates Pydantic AI RunContext for type-safe DI
"""

import os
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from dependencies import AgentDependencies
from dotenv import load_dotenv
import logging

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OrderInfo(BaseModel):
    """Order information model."""

    order_id: str
    status: str
    customer_email: str
    total: float
    created_at: str = ""


# Create agent with dependency type
order_agent = Agent(
    os.getenv("AI_MODEL", "openai:gpt-5.4-mini"),
    deps_type=AgentDependencies,
    system_prompt="""You are an order management agent for an e-commerce platform.
    
    Your responsibilities:
    - Help customers track their orders
    - Provide order status updates
    - Send notifications when requested
    - Resolve order-related issues
    
    Use the available tools to access order information and send updates.
    Always be helpful, professional, and accurate.""",
)


@order_agent.tool
async def get_order(ctx: RunContext[AgentDependencies], order_id: str) -> OrderInfo:
    """
    Lookup order information by ID.

    Uses injected database and cache dependencies.
    Implements cache-aside pattern for performance.

    Args:
        ctx: RunContext with injected dependencies
        order_id: Order ID to lookup

    Returns:
        Order information
    """
    cache_key = f"order:{order_id}"

    # Try cache first
    cached = await ctx.deps.cache.get(cache_key)
    if cached is not None:
        return OrderInfo(**cached)

    # Cache miss: query database
    results = await ctx.deps.database.query(
        "SELECT id, status, customer_email, total, created_at FROM orders WHERE id = :id",
        {"id": order_id},
    )

    if not results:
        raise ValueError(f"Order {order_id} not found")

    row = results[0]
    order = OrderInfo(
        order_id=row["id"],
        status=row["status"],
        customer_email=row["customer_email"],
        total=row["total"],
        created_at=row.get("created_at", ""),
    )

    # Populate cache for future lookups
    await ctx.deps.cache.set(cache_key, order.model_dump())

    return order
@order_agent.tool
async def send_order_update(
    ctx: RunContext[AgentDependencies], order_id: str, message: str
) -> bool:
    """
    Send order update email to customer.

    Uses injected email service.

    Args:
        ctx: RunContext with injected dependencies
        order_id: Order ID
        message: Update message to send

    Returns:
        True if email sent successfully
    """
    logger.info(f"Sending update for order {order_id}")

    # Get order info to get customer email
    order = await get_order(ctx, order_id)

    # Check if email notifications are enabled
    if not ctx.deps.config.get_feature("email_notifications", True):
        logger.warning("Email notifications disabled in config")
        return False

    # Send email via injected service
    success = await ctx.deps.email.send(
        to=order.customer_email, subject=f"Order {order_id} Update", body=message
    )

    logger.info(f"Email sent to {order.customer_email}: {success}")
    return success


@order_agent.tool
async def check_feature_enabled(
    ctx: RunContext[AgentDependencies], feature: str
) -> bool:
    """
    Check if a feature is enabled in configuration.

    Uses injected config dependency.

    Args:
        ctx: RunContext with injected dependencies
        feature: Feature name to check

    Returns:
        True if feature is enabled
    """
    enabled = ctx.deps.config.get_feature(feature, False)
    logger.info(f"Feature '{feature}' enabled: {enabled}")
    return enabled


@order_agent.tool
async def search_orders(
    ctx: RunContext[AgentDependencies], customer_email: str
) -> list[OrderInfo]:
    """
    Search orders by customer email.

    Args:
        ctx: RunContext with injected dependencies
        customer_email: Customer email address

    Returns:
        List of orders for customer
    """
    logger.info(f"Searching orders for customer: {customer_email}")

    # Query database
    results = await ctx.deps.database.query(
        "SELECT * FROM orders WHERE customer_email = :email", {"email": customer_email}
    )

    # Convert results to OrderInfo objects
    orders = [
        OrderInfo(
            order_id=row["id"],
            status=row["status"],
            customer_email=row["customer_email"],
            total=row["total"],
            created_at=row.get("created_at", ""),
        )
        for row in results
    ]

    logger.info(f"Found {len(orders)} orders for {customer_email}")
    return orders


async def process_order_query(query: str, deps: AgentDependencies) -> str:
    """
    Process order-related query with dependencies.

    Args:
        query: Customer query
        deps: AgentDependencies instance with all resources

    Returns:
        Agent response
    """
    # YOUR CODE HERE
    pass
# Example usage
async def main():
    """Example of using agent with dependencies."""
    from factory import DependencyFactory

    # YOUR CODE HERE
    pass
if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
