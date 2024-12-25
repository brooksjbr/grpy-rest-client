from aiohttp import ClientSession

from grpy.base_rest_client import BaseRestClient


class AsyncRestClient(BaseRestClient):
    """Async REST client for making HTTP requests."""

    def __init__(self, url: str, method: str = "GET", endpoint: str = ""):
        """Initialize the API client with a URL"""
        super().__init__(url, method, endpoint)
        self.url = url
        self.method = method
        self.endpoint = endpoint
        self.headers = {}
        self.params = {}
        self.data = {}
        self.json = {}
        self.files = {}
        self.session = None

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

    # TODO: Implement additional request parameters
    # params=self.params,
    # data=self.data,
    # json=self.json,
    # files=self.files,
    async def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        response = await self.session.request(
            method=self.method,
            url=self.url,
            headers=self.headers,
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
