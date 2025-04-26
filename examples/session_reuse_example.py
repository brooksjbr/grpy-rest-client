import asyncio

from aiohttp import ClientSession, TCPConnector

from grpy.rest_client import RestClient


async def main():
    # Create a shared session with custom settings
    # - Limit connection pool size
    # - Set keep-alive timeout
    # - Configure SSL
    shared_session = ClientSession(
        connector=TCPConnector(
            limit=20,  # Maximum number of connections
            ttl_dns_cache=300,  # DNS cache TTL in seconds
            ssl=False,  # Disable SSL verification for testing
        ),
        timeout=30,  # Default timeout for all requests
    )

    # Use the session with context manager to ensure proper cleanup
    async with shared_session:
        try:
            # First client for authentication
            auth_client = RestClient(
                url="https://api.example.com",
                endpoint="/auth/login",
                method="POST",
                session=shared_session,  # Reuse the shared session
                data={"username": "user123", "password": "securepassword"},
            )

            # Use auth_client with its own context (won't close the shared session)
            async with auth_client:
                auth_response = await auth_client.handle_request()
                auth_data = await auth_response.json()
                token = auth_data.get("token")

                # The session now has authentication cookies/state

            # Create a second client for fetching user data
            # Reusing the same session that now has auth state
            user_client = RestClient(
                url="https://api.example.com",
                endpoint="/users/profile",
                method="GET",
                session=shared_session,  # Reuse the shared session with auth state
                headers={"Authorization": f"Bearer {token}"},
            )

            async with user_client:
                user_response = await user_client.handle_request()
                user_data = await user_response.json()
                print(f"User profile: {user_data}")

            # Create a third client for fetching user orders
            # Again reusing the same session
            orders_client = RestClient(
                url="https://api.example.com",
                endpoint="/users/orders",
                method="GET",
                session=shared_session,  # Reuse the shared session
                headers={"Authorization": f"Bearer {token}"},
            )

            # Use pagination with the shared session
            async with orders_client:
                async for page in orders_client.paginate(data_key="orders", max_pages=5):
                    for order in page:
                        print(f"Order ID: {order['id']}, Status: {order['status']}")

        except Exception as e:
            print(f"Error occurred: {e}")


# Run the example
asyncio.run(main())
