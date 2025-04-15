from asyncio import TimeoutError
from typing import Any, AsyncContextManager, ClassVar, Dict, Optional, Set
from urllib.parse import urljoin

from aiohttp import ClientSession, ClientTimeout
from pydantic import BaseModel, ConfigDict, Field, field_validator


class RestClient(BaseModel, AsyncContextManager["RestClient"]):
    """Async REST client for making HTTP requests."""

    url: str
    method: str = "GET"
    endpoint: str = ""
    timeout: Optional[float] = 60
    session: Optional[ClientSession] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = None
    timeout_obj: Optional[ClientTimeout] = None  # Add this field

    # Class variables need to be annotated with ClassVar
    VALID_METHODS: ClassVar[Set[str]] = {
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "HEAD",
    }
    DEFAULT_TIMEOUT: ClassVar[int] = 60
    DEFAULT_USER_AGENT: ClassVar[str] = "grpy-rest-client/0.1.0"

    DEFAULT_HEADERS: ClassVar[Dict[str, str]] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }

    # Use ConfigDict instead of class Config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        super().__init__(**data)
        if self.headers is None:
            self.headers = self.DEFAULT_HEADERS.copy()
        else:
            default_headers = self.DEFAULT_HEADERS.copy()
            default_headers.update(self.headers)
            self.headers = default_headers

        self.timeout_obj = ClientTimeout(total=self.timeout)

    @field_validator("method")
    @classmethod
    def validate_http_method(cls, method):
        if method.upper() not in cls.VALID_METHODS:
            raise ValueError(
                f"Invalid HTTP method: {method}. Valid methods are {cls.VALID_METHODS}"
            )
        return method.upper()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, timeout):
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(
                f"Timeout must be a positive number, got {timeout}"
            )
        return timeout

    async def __aenter__(self):
        """Enter the context manager."""
        self.session = ClientSession(
            timeout=self.timeout_obj, raise_for_status=True
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        if self.session and not self.session.closed:
            await self.session.close()

    def handle_exception(method):
        async def wrapper(self, *args, **kwargs):
            try:
                return await method(self, *args, **kwargs)
            except TimeoutError as e:
                raise TimeoutError(f"Request timed out: {e}") from e
            except Exception as exc:
                raise exc from exc

        return wrapper

    @handle_exception
    async def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        request_url = (
            urljoin(self.url, self.endpoint) if self.endpoint else self.url
        )
        response = await self.session.request(
            method=self.method,
            url=request_url,
            headers=self.headers,
            params=self.params,
            timeout=self.timeout_obj,
            **kwargs,
        )

        return response

    def update_headers(self, headers: dict):
        """Update headers for the request."""
        self.headers.update(headers)

    def update_params(self, params: dict):
        """Update request parameters.

        Args:
            params (dict): Dictionary of query parameters to update or add
        """
        self.params.update(params)

    def update_timeout(self, timeout: float):
        """Update the client timeout value.

        Args:
            timeout (float): New timeout value in seconds
        """
        self.timeout = timeout
        self.timeout_obj = ClientTimeout(total=timeout)
        if self.session:
            self.session._timeout = self.timeout_obj
