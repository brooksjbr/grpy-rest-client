from aiohttp import ClientSession, ClientTimeout

from grpy.base_rest_client import BaseRestClient


class AsyncRestClient(BaseRestClient):
    """Async REST client for making HTTP requests."""

    def __init__(self, url: str, method: str = "GET", endpoint: str = ""):
        """Initialize the API client with a URL"""
        self.url = url.strip("/")
        self.method = method.upper()
        self.endpoint = endpoint.strip("/")
        self.headers = {}
        self.timeout = ClientTimeout(total=60)
        self.session = None

        if self.method not in self.VALID_METHODS:
            raise ValueError(f"Invalid HTTP method: {self.method}")

    async def __aenter__(self):
        """Enter the context manager."""
        self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self.session:
            await self.session.close()

    async def update_headers(self, headers: dict):
        """Set headers for the request."""
        self.headers.update(headers)

    async def handle_request(self, timeout: int, **kwargs):
        """Make a REST request with specified parameters."""
        if self.endpoint:
            self.url = f"{self.url}/{self.endpoint}"

        if timeout:
            self.timeout = ClientTimeout(total=timeout)

        response = await self.session.request(
            method=self.method,
            url=self.url,
            headers=self.headers,
            timeout=self.timeout,
            **kwargs,
        )
        return response

    async def handle_exception(self):
        """Handle HTTP requests and exceptions."""
        try:
            response = await self.handle_request()
            response.raise_for_status()
            return response
        except Exception as e:
            raise e
