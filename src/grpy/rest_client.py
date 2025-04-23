import asyncio
from asyncio import TimeoutError
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
)
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponse, ClientResponseError, ClientSession, ClientTimeout
from aiohttp import ContentTypeError as AiohttpContentTypeError
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .pagination import HateoasPaginationStrategy, PageNumberPaginationStrategy, PaginationStrategy


class RestClientError(Exception):
    """Base exception for REST client errors."""

    pass


class ServerError(RestClientError):
    """Exception for 5xx server errors."""

    pass


class AuthenticationError(ClientError):
    """Exception for 401 authentication errors."""

    pass


class ForbiddenError(ClientError):
    """Exception for 403 forbidden errors."""

    pass


class RateLimitError(ClientError):
    """Exception for 429 rate limit errors."""

    pass


class ContentTypeError(RestClientError):
    """Exception for content type errors."""

    pass


def handle_exception(method):
    async def wrapper(self, *args, **kwargs):
        try:
            response = await method(self, *args, **kwargs)

            # Check status codes
            if 400 <= response.status < 500:
                error_text = await response.text()

                # Define error messages for specific status codes
                error_messages = {
                    401: "Authentication required",
                    403: "Access forbidden",
                    404: "Resource not found",
                    429: "Rate limit exceeded",
                }

                # Get the specific error message or use a default
                message = f"{error_messages.get(response.status, 'Client error')}: {error_text}"

                raise ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=message,
                )

            elif 500 <= response.status < 600:
                error_text = await response.text()
                raise ServerError(f"Server error {response.status}: {error_text}")

            return response

        except TimeoutError as e:
            raise TimeoutError(f"Request timed out: {e}") from e
        except ClientResponseError:
            # Re-raise ClientResponseError exceptions
            raise
        except AiohttpContentTypeError as e:
            raise AiohttpContentTypeError(f"Content type error: {e}") from e
        except Exception as exc:
            raise ClientResponseError(
                request_info=None, history=None, status=0, message=f"Unexpected error: {exc}"
            ) from exc

    return wrapper


class RestClient(BaseModel, AsyncContextManager["RestClient"]):
    """Async REST client for making HTTP requests."""

    url: str
    method: str = "GET"
    endpoint: str = ""
    timeout: Optional[float] = 60
    session: Optional[ClientSession] = None
    params: Dict[str, Any] = Field(default_factory=dict)
    headers: Dict[str, str] = None
    timeout_obj: Optional[ClientTimeout] = None
    pagination_strategy: Optional[PaginationStrategy] = None
    data: Optional[Dict[str, Any]] = Field(default=None)

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

    # Available pagination strategies
    PAGINATION_STRATEGIES: ClassVar[Dict[str, Type[PaginationStrategy]]] = {
        "page_number": PageNumberPaginationStrategy,
        "hateoas": HateoasPaginationStrategy,
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

        # Default to HATEOAS pagination strategy if none is provided
        if self.pagination_strategy is None:
            self.pagination_strategy = HateoasPaginationStrategy()

    async def __aenter__(self) -> "RestClient":
        """Async context manager entry point."""
        if self.session is None:
            self.session = ClientSession()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit point."""
        await self.close()

    def __del__(self) -> None:
        """Ensure session is closed when object is garbage collected."""
        if hasattr(self, "session") and self.session and not self.session.closed:
            import warnings

            warnings.warn(
                "RestClient was garbage collected with an open session. "
                "Please use 'async with' context manager or explicitly call 'await client.close()' "
                "to ensure proper resource cleanup.",
                ResourceWarning,
                stacklevel=2,
            )

            # Schedule the session for closing if possible
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
            except Exception:
                pass  # Best effort cleanup

    @field_validator("method")
    @classmethod
    def validate_http_method(cls, method: str) -> str:
        if method.upper() not in cls.VALID_METHODS:
            raise ValueError(
                f"Invalid HTTP method: {method}. Valid methods are {cls.VALID_METHODS}"
            )
        return method.upper()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, timeout: Union[int, float]) -> Union[int, float]:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(f"Timeout must be a positive number, got {timeout}")
        return timeout

    async def close(self) -> None:
        """Explicitly close the session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    @handle_exception
    async def handle_request(self, **kwargs) -> ClientResponse:
        """Make a REST request with specified parameters."""
        request_url = urljoin(self.url, self.endpoint) if self.endpoint else self.url

        # Include data in the request if it's provided
        if self.data is not None and self.method in ["POST", "PUT", "PATCH"]:
            kwargs["json"] = self.data

        response = await self.session.request(
            method=self.method,
            url=request_url,
            headers=self.headers,
            params=self.params,
            timeout=self.timeout_obj,
            **kwargs,
        )

        return response

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update headers for the request."""
        self.headers.update(headers)

    def update_params(self, params: Dict[str, Any]) -> None:
        """Update request parameters.

        Args:
            params (dict): Dictionary of query parameters to update or add
        """
        self.params.update(params)

    def update_timeout(self, timeout: float) -> None:
        """Update the client timeout value.

        Args:
            timeout (float): New timeout value in seconds
        """
        self.timeout = timeout
        self.timeout_obj = ClientTimeout(total=timeout)
        if self.session:
            self.session._timeout = self.timeout_obj

    def update_data(self, data: Dict[str, Any]) -> None:
        """Update request data for POST/PUT/PATCH requests.

        Args:
            data (dict): Dictionary of data to update or add
        """
        if self.data is None:
            self.data = {}
        self.data.update(data)

    def set_pagination_strategy(
        self, strategy_name: Optional[str] = None, strategy: Optional[PaginationStrategy] = None
    ) -> None:
        """Set the pagination strategy to use.

        Args:
            strategy_name: Name of a built-in strategy ('page_number' or 'hateoas')
            strategy: Custom PaginationStrategy instance

        Raises:
            ValueError: If neither strategy_name nor strategy is provided, or if
                        strategy_name is not a valid built-in strategy
        """
        if strategy is not None:
            self.pagination_strategy = strategy
        elif strategy_name is not None:
            if strategy_name not in self.PAGINATION_STRATEGIES:
                raise ValueError(
                    f"Invalid pagination strategy: {strategy_name}. "
                    f"Valid strategies are {list(self.PAGINATION_STRATEGIES.keys())}"
                )
            self.pagination_strategy = self.PAGINATION_STRATEGIES[strategy_name]()
        else:
            raise ValueError("Either strategy_name or strategy must be provided")

    async def paginate(
        self,
        data_key: Optional[str] = None,
        max_pages: Optional[int] = None,
        request_kwargs: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[List[Dict[str, Any]]]:
        """
        Paginate through API results using the configured pagination strategy.

        Args:
            data_key (str, optional): The key in the response that contains the data items.
            max_pages (int, optional): Maximum number of pages to retrieve.
            request_kwargs (dict, optional): Additional kwargs to pass to handle_request.

        Yields:
            list: The data items from each page.

        Raises:
            ValueError: If no pagination strategy is configured
        """
        if self.pagination_strategy is None:
            raise ValueError("No pagination strategy configured")

        page_count = 0
        current_params = self.params.copy()
        request_kwargs = request_kwargs or {}

        while True:
            # Check if we've reached the maximum number of pages
            if max_pages is not None and page_count >= max_pages:
                break

            # Update the client's params for this request
            self.params = current_params.copy()

            # Make the request
            response = await self.handle_request(**request_kwargs)
            response_json = await response.json()

            # Extract the data from the response using the pagination strategy
            data_items = self.pagination_strategy.extract_data(response_json, data_key)

            # Yield the data items from this page
            yield data_items

            # Increment the page count
            page_count += 1

            # Determine if there are more pages and what the next page parameters should be
            has_more, next_params = self.pagination_strategy.get_next_page_info(
                response_json, current_params
            )

            if not has_more:
                break

            # Update the parameters for the next page
            current_params = next_params
