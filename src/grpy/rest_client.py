from asyncio import TimeoutError
from contextlib import AsyncExitStack
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

from aiohttp import ClientResponse, ClientResponseError, ClientSession, ClientTimeout
from aiohttp import ContentTypeError as AiohttpContentTypeError
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .logging import DefaultLogger, Logger
from .pagination import HateoasPaginationStrategy, PageNumberPaginationStrategy, PaginationStrategy


class RestClientError(Exception):
    """Base exception for REST client errors."""

    pass


class ServerError(RestClientError):
    """Exception for 5xx server errors."""

    pass


def handle_exception(method):
    async def wrapper(self, *args, **kwargs):
        try:
            self.logger.debug(
                f"Executing {method.__name__} request",
                url=urljoin(self.url, self.endpoint) if self.endpoint else self.url,
                method=self.method,
            )

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

                self.logger.error(
                    f"Client error in {method.__name__}",
                    status=response.status,
                    error_details=message,
                )  # Changed 'message' to 'error_details'

                raise ClientResponseError(
                    request_info=response.request_info,
                    history=response.history,
                    status=response.status,
                    message=message,
                )

            elif 500 <= response.status < 600:
                error_text = await response.text()
                self.logger.error(
                    f"Server error in {method.__name__}",
                    status=response.status,
                    error_details=error_text,
                )  # Changed 'message' to 'error_details'
                raise ServerError(f"Server error {response.status}: {error_text}")

            self.logger.debug(
                f"Request {method.__name__} completed successfully", status=response.status
            )
            return response

        except TimeoutError as e:
            self.logger.error(f"Request timeout in {method.__name__}", error=str(e))
            raise TimeoutError(f"Request timed out: {e}") from e
        except ClientResponseError as e:
            # Re-raise ClientResponseError exceptions
            self.logger.error(
                f"Client response error in {method.__name__}",
                status=getattr(e, "status", "unknown"),
                error_details=str(e),
            )  # Changed 'message' to 'error_details'
            raise
        except AiohttpContentTypeError as e:
            self.logger.error(f"Content type error in {method.__name__}", error=str(e))
            raise AiohttpContentTypeError(f"Content type error: {e}") from e
        except Exception as exc:
            self.logger.error(f"Unexpected error in {method.__name__}", error=str(exc))
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
    content_type: str = "application/json"
    logger: Optional[Logger] = None
    _exit_stack: Optional[AsyncExitStack] = None

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

        if self.logger is None:
            self.logger = DefaultLogger()

        self._exit_stack = AsyncExitStack()

        self.logger.info(
            "RestClient initialized", url=self.url, method=self.method, timeout=self.timeout
        )

    async def __aenter__(self) -> "RestClient":
        """Async context manager entry point."""
        self.logger.debug("Entering RestClient context")

        # Create exit stack for managing resources
        if self._exit_stack is None:
            self._exit_stack = AsyncExitStack()

        # If a session was provided externally, use it without adding to exit stack
        # (the caller is responsible for its lifecycle)
        if self.session is None:
            self.logger.debug("Creating new ClientSession")
            self.session = ClientSession()
            # Add session to exit stack so it will be automatically closed
            await self._exit_stack.enter_async_context(self.session)
        else:
            self.logger.debug("Using existing ClientSession")

        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit point."""
        self.logger.debug("Exiting RestClient context")
        if self._exit_stack is not None:
            try:
                await self._exit_stack.aclose()
            except Exception as e:
                self.logger.error(f"Error during client cleanup: {e}")
            finally:
                self._exit_stack = None
                self.session = None

    @staticmethod
    def _cleanup_session(session):
        """Static method to clean up session without reference to self."""
        if session and not session.closed:
            import asyncio

            try:
                # Try to get the current event loop
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(session.close())
                else:
                    # If loop isn't running, create a new one just for cleanup
                    new_loop = asyncio.new_event_loop()
                    new_loop.run_until_complete(session.close())
                    new_loop.close()
            except Exception:
                # Last resort: try to close synchronously if possible
                # This isn't ideal but better than leaking resources
                if hasattr(session, "_connector") and hasattr(session._connector, "_close"):
                    session._connector._close()

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
        if self._exit_stack is not None:
            self.logger.debug("Closing client session")
            await self._exit_stack.aclose()
            self._exit_stack = None
            self.session = None

            # Deactivate finalizer since we've manually cleaned up
            if self._finalizer is not None:
                self._finalizer.detach()
                self._finalizer = None
                self.logger.debug("Detached session cleanup finalizer")

    @handle_exception
    async def handle_request(self, **kwargs) -> ClientResponse:
        """Make a REST request with specified parameters."""
        request_url = urljoin(self.url, self.endpoint) if self.endpoint else self.url

        # Include data in the request if it's provided
        if self.content_type == "application/json" and self.data is not None:
            kwargs["json"] = self.data
            self.logger.debug("Adding JSON data to request", data_size=len(str(self.data)))
        elif self.data is not None:
            kwargs["data"] = self.data
            self.logger.debug("Adding form data to request", data_size=len(str(self.data)))

        self.logger.info(f"Making {self.method} request", url=request_url, params=self.params)

        response = await self.session.request(
            method=self.method,
            url=request_url,
            headers=self.headers,
            params=self.params,
            timeout=self.timeout_obj,
            **kwargs,
        )

        self.logger.info(
            "Received response",
            status=response.status,
            content_type=response.headers.get("Content-Type"),
        )

        return response

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update headers for the request."""
        self.logger.debug("Updating request headers", new_headers=headers)
        self.headers.update(headers)

    def update_params(self, params: Dict[str, Any]) -> None:
        """Update request parameters.

        Args:
            params (dict): Dictionary of query parameters to update or add
        """
        self.logger.debug("Updating request parameters", new_params=params)
        self.params.update(params)

    def update_timeout(self, timeout: float) -> None:
        """Update the client timeout value.

        Args:
            timeout (float): New timeout value in seconds
        """
        self.logger.debug("Updating timeout", old_timeout=self.timeout, new_timeout=timeout)
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
        self.logger.debug("Updating request data", data_keys=list(data.keys()))
        self.data.update(data)

    def set_content_type(self, content_type: str) -> None:
        """Set the content type for requests."""
        self.logger.debug("Setting content type", old_type=self.content_type, new_type=content_type)
        self.content_type = content_type
        self.headers["Content-Type"] = content_type

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
            self.logger.info(
                "Setting custom pagination strategy", strategy_type=strategy.__class__.__name__
            )
            self.pagination_strategy = strategy
        elif strategy_name is not None:
            if strategy_name not in self.PAGINATION_STRATEGIES:
                self.logger.error(
                    "Invalid pagination strategy",
                    strategy_name=strategy_name,
                    valid_strategies=list(self.PAGINATION_STRATEGIES.keys()),
                )
                raise ValueError(
                    f"Invalid pagination strategy: {strategy_name}. "
                    f"Valid strategies are {list(self.PAGINATION_STRATEGIES.keys())}"
                )
            self.logger.info("Setting built-in pagination strategy", strategy_name=strategy_name)
            self.pagination_strategy = self.PAGINATION_STRATEGIES[strategy_name]()
        else:
            self.logger.error("No pagination strategy provided")
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
            self.logger.error("Pagination attempted without a strategy")
            raise ValueError("No pagination strategy configured")

        self.logger.info(
            "Starting pagination",
            data_key=data_key,
            max_pages=max_pages,
            strategy=self.pagination_strategy.__class__.__name__,
        )

        page_count = 0
        current_params = self.params.copy()
        request_kwargs = request_kwargs or {}

        while True:
            # Check if we've reached the maximum number of pages
            if max_pages is not None and page_count >= max_pages:
                self.logger.info("Reached maximum number of pages", max_pages=max_pages)
                break

            # Update the client's params for this request
            self.params = current_params.copy()
            self.logger.debug(f"Fetching page {page_count + 1}", params=self.params)

            # Make the request
            response = await self.handle_request(**request_kwargs)
            try:
                response_json = await response.json()
                self.logger.debug("Successfully parsed JSON response")
            except AiohttpContentTypeError as e:
                self.logger.error("Failed to parse JSON response", error=str(e))
                raise RestClientError(f"Failed to parse JSON response: {e}") from e

            # Extract the data from the response using the pagination strategy
            data_items = self.pagination_strategy.extract_data(response_json, data_key)
            self.logger.debug(
                f"Extracted data from page {page_count + 1}",
                items_count=len(data_items) if isinstance(data_items, list) else "unknown",
            )

            # Yield the data items from this page
            yield data_items

            # Increment the page count
            page_count += 1

            # Determine if there are more pages and what the next page parameters should be
            has_more, next_params = self.pagination_strategy.get_next_page_info(
                response_json, current_params
            )

            if not has_more:
                self.logger.info("No more pages available", total_pages=page_count)
                break

            # Update the parameters for the next page
            current_params = next_params
            self.logger.debug("Moving to next page", next_params=next_params)
