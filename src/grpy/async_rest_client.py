from aiohttp import ClientSession, ClientTimeout

from grpy.base_rest_client import BaseRestClient

# Define the default timeout at module level
DEFAULT_TIMEOUT = ClientTimeout(total=60)


class AsyncRestClient(BaseRestClient):
    """Async REST client for making HTTP requests."""

    def __init__(
        self,
        url: str,
        method: str = "GET",
        endpoint: str = "",
        timeout: ClientTimeout = DEFAULT_TIMEOUT,
    ):
        """Initialize the API client with a URL"""
        self.url = url.strip("/")
        self.method = method.upper()
        self.endpoint = endpoint.strip("/")
        self.headers = {}
        self.timeout = timeout
        self.session = None

        if self.method not in self.VALID_METHODS:
            raise ValueError(f"Invalid HTTP method: {self.method}")

    async def __aenter__(self):
        """Enter the context manager."""
        self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        await self.session.close()

    async def update_headers(self, headers: dict):
        """Update headers for the request."""
        self.headers.update(headers)

    def handle_exception(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                raise exc

        return wrapper

    @handle_exception
    async def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        if self.endpoint:
            self.url = f"{self.url}/{self.endpoint}"

        response = await self.session.request(
            method=self.method,
            url=self.url,
            headers=self.headers,
            timeout=self.timeout,
            **kwargs,
        )
        return response
