from contextlib import AsyncExitStack
from typing import Any, AsyncContextManager, ClassVar, Dict, List, Optional, Set, Union

from aiohttp import ClientSession, ClientTimeout
from pydantic import BaseModel, ConfigDict, Field

from . import __version__
from .logging import DefaultLogger, Logger
from .pagination_manager import PaginationManager
from .pagination_strategy_protocol import PaginationStrategy
from .retry_manager import RetryManager, RetryPolicy


class RestClientError(Exception):
    """Base exception for REST client errors."""

    pass


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
    pagination_strategy: Optional[Union[str, PaginationStrategy]] = None
    retry_policy: Optional[Union[str, RetryPolicy]] = None
    data: Optional[Dict[str, Any]] = Field(default=None)
    content_type: str = "application/json"
    logger: Optional[Logger] = None
    _exit_stack: Optional[AsyncExitStack] = None
    _pagination_manager: Optional[PaginationManager] = None
    _retry_manager: Optional[RetryManager] = None

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
    DEFAULT_USER_AGENT: ClassVar[str] = f"grpy-rest-client/{__version__}"

    DEFAULT_HEADERS: ClassVar[Dict[str, str]] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }

    # Use ConfigDict instead of class Config
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def __init__(self, **data):
        # Validate and normalize HTTP method
        if "method" in data:
            data["method"] = data["method"].upper()
            if data["method"] not in self.VALID_METHODS:
                raise ValueError(f"Invalid HTTP method: {data['method']}")

        # Validate timeout
        if "timeout" in data:
            timeout = data["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                raise ValueError("Timeout must be a positive number")

        super().__init__(**data)
        if self.headers is None:
            self.headers = self.DEFAULT_HEADERS.copy()
        else:
            default_headers = self.DEFAULT_HEADERS.copy()
            default_headers.update(self.headers)
            self.headers = default_headers

        self.timeout_obj = ClientTimeout(total=self.timeout)

        # Initialize logger if not provided
        if self.logger is None:
            self.logger = DefaultLogger(name="grpy-rest-client")

        # Initialize managers
        self._initialize_managers()

        # Initialize pagination strategy
        self._initialize_pagination_strategy()

        # Initialize retry policy
        self._initialize_retry_policy()

    def _initialize_managers(self):
        """Initialize the pagination and retry managers."""
        # Create pagination manager if not already set
        if self._pagination_manager is None:
            self._pagination_manager = PaginationManager(logger=self.logger)
            self._pagination_manager.register_builtin_strategies()

        # Create retry manager if not already set
        if self._retry_manager is None:
            self._retry_manager = RetryManager(logger=self.logger)
            self._retry_manager.register_builtin_policies()

    def _initialize_pagination_strategy(self):
        """Initialize the pagination strategy based on configuration."""
        if self.pagination_strategy is None:
            # Use the default strategy from the manager
            self.pagination_strategy = self._pagination_manager.get_strategy()
        elif isinstance(self.pagination_strategy, str):
            # Get the strategy by name from the manager
            self.pagination_strategy = self._pagination_manager.get_strategy(
                self.pagination_strategy
            )
        # If it's already a PaginationStrategy instance, keep it as is

    def _initialize_retry_policy(self):
        """Initialize the retry policy based on configuration."""
        if self.retry_policy is None:
            # Use the default policy from the manager
            self.retry_policy = self._retry_manager.get_policy()
        elif isinstance(self.retry_policy, str):
            # Get the policy by name from the manager
            self.retry_policy = self._retry_manager.get_policy(self.retry_policy)
        # If it's already a RetryPolicy instance, keep it as is

    async def __aenter__(self) -> "RestClient":
        """Enter the async context manager."""
        self._exit_stack = AsyncExitStack()
        if self.session is None:
            self.session = await self._exit_stack.enter_async_context(ClientSession())
        else:
            # Mark this as an external session so we don't close it
            self.session._external = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        try:
            if self._exit_stack:
                await self._exit_stack.aclose()
        finally:
            self._exit_stack = None
            # Only set session to None if we created it
            if self.session and not hasattr(self.session, "_external"):
                self.session = None

    async def request(
        self,
        method: Optional[str] = None,
        endpoint: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ):
        """Make an HTTP request.

        Args:
            method: HTTP method to use (overrides instance method)
            endpoint: API endpoint to call (appended to base URL)
            params: Query parameters to include
            data: Request body data
            headers: Additional headers to include
            timeout: Request timeout in seconds

        Returns:
            Response from the API
        """
        # Use instance values as defaults
        method = method or self.method
        endpoint = endpoint or self.endpoint

        # Merge parameters, with provided params taking precedence
        merged_params = self.params.copy()
        if params:
            merged_params.update(params)

        # Merge headers, with provided headers taking precedence
        merged_headers = self.headers.copy()
        if headers:
            merged_headers.update(headers)

        # Use provided data or instance data
        request_data = data if data is not None else self.data

        # Build the full URL
        url = f"{self.url.rstrip('/')}/{endpoint.lstrip('/')}" if endpoint else self.url

        # Use provided timeout or instance timeout
        timeout_obj = ClientTimeout(total=timeout) if timeout else self.timeout_obj

        # Validate the HTTP method
        method = method.upper()
        if method not in self.VALID_METHODS:
            raise RestClientError(f"Invalid HTTP method: {method}")

        # Log the request
        self.logger.debug(
            f"Making {method} request to {url} with params={merged_params}, "
            f"headers={merged_headers}, data={request_data}"
        )

        # Use the retry policy to execute the request with retries
        async def execute_request():
            if self.session is None:
                raise RestClientError("Session not initialized. Use async with context.")

            return await self.session.request(
                method=method,
                url=url,
                params=merged_params,
                json=request_data,
                headers=merged_headers,
                timeout=timeout_obj,
            )

        response = await self.retry_policy.execute_with_retry(execute_request)

        # Log the response
        self.logger.debug(f"Received response: status={response.status}")

        return response

    async def get_all_pages(
        self,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        max_pages: Optional[int] = None,
    ) -> List[Any]:
        """Fetch all pages of results using the pagination strategy.

        Args:
            endpoint: API endpoint to call (appended to base URL)
            method: HTTP method to use (overrides instance method)
            params: Initial query parameters
            data: Request body data
            headers: Additional headers to include
            timeout: Request timeout in seconds
            max_pages: Maximum number of pages to fetch (None for all)

        Returns:
            List of all items from all pages

        Raises:
            RestClientError: If pagination fails
        """
        self.logger.debug(f"Fetching all pages from {endpoint or self.endpoint}")

        if not self.pagination_strategy:
            raise RestClientError("No pagination strategy configured")

        current_params = params.copy() if params else {}
        page_count = 0
        all_items = []

        while True:
            # Check if we've reached the maximum number of pages
            if max_pages is not None and page_count >= max_pages:
                self.logger.info(f"Reached maximum page count: {max_pages}")
                break

            # Make the request for the current page
            response = await self.request(
                method=method,
                endpoint=endpoint,
                params=current_params,
                data=data,
                headers=headers,
                timeout=timeout,
            )

            try:
                # Parse the response
                response_data = await response.json()
            except Exception as e:
                raise RestClientError(f"Failed to parse JSON response: {str(e)}") from None

            # Extract items from the response using the pagination strategy
            items = self.pagination_strategy.extract_items(response_data)
            all_items.extend(items)

            # Get information about the next page
            has_more, next_params = self.pagination_strategy.get_next_page_info(
                response_data, current_params
            )

            # Update page count
            page_count += 1

            # Log progress
            self.logger.debug(f"Fetched page {page_count} with {len(items)} items")

            # Break if there are no more pages
            if not has_more:
                self.logger.debug("No more pages available")
                break

            # Update parameters for the next page
            current_params = next_params

        self.logger.info(f"Fetched {len(all_items)} items from {page_count} pages")
        return all_items

    # Convenience methods for common HTTP methods
    async def get(self, endpoint="", **kwargs):
        """Make a GET request."""
        return await self.request(method="GET", endpoint=endpoint, **kwargs)

    async def post(self, endpoint="", data=None, **kwargs):
        """Make a POST request."""
        return await self.request(method="POST", endpoint=endpoint, data=data, **kwargs)

    async def put(self, endpoint="", data=None, **kwargs):
        """Make a PUT request."""
        return await self.request(method="PUT", endpoint=endpoint, data=data, **kwargs)

    async def delete(self, endpoint="", **kwargs):
        """Make a DELETE request."""
        return await self.request(method="DELETE", endpoint=endpoint, **kwargs)

    async def patch(self, endpoint="", data=None, **kwargs):
        """Make a PATCH request."""
        return await self.request(method="PATCH", endpoint=endpoint, data=data, **kwargs)

    # Manager access methods
    def get_pagination_manager(self) -> PaginationManager:
        """Get the pagination manager instance."""
        return self._pagination_manager

    def get_retry_manager(self) -> RetryManager:
        """Get the retry manager instance."""
        return self._retry_manager

    def set_pagination_strategy(self, strategy: Union[str, PaginationStrategy]) -> None:
        """
        Set the pagination strategy to use.

        Args:
            strategy: Either a strategy name or a PaginationStrategy instance
        """
        if isinstance(strategy, str):
            self.pagination_strategy = self._pagination_manager.get_strategy(strategy)
        else:
            self.pagination_strategy = strategy

    def set_retry_policy(self, policy: Union[str, RetryPolicy]) -> None:
        """
        Set the retry policy to use.

        Args:
            policy: Either a policy name or a RetryPolicy instance
        """
        if isinstance(policy, str):
            self.retry_policy = self._retry_manager.get_policy(policy)
        else:
            self.retry_policy = policy

    def update_headers(self, headers: Dict[str, str]) -> None:
        """Update the headers for this client.

        Args:
            headers: New headers to add or update
        """
        if not self.headers:
            self.headers = {}
        self.headers.update(headers)
        self.logger.debug(f"Updated headers: {headers}")

    def update_params(self, params: Dict[str, Any]) -> None:
        """Update the query parameters for this client.

        Args:
            params: New parameters to add or update
        """
        if not self.params:
            self.params = {}
        self.params.update(params)
        self.logger.debug(f"Updated params: {params}")

    def update_timeout(self, timeout: float) -> None:
        """Update the timeout for this client.

        Args:
            timeout: New timeout value in seconds
        """
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("Timeout must be a positive number")

        self.timeout = timeout
        self.timeout_obj = ClientTimeout(total=timeout)

        # Update session timeout if session exists
        if self.session:
            self.session._timeout = self.timeout_obj

        self.logger.debug(f"Updated timeout to {timeout}s")

    def update_data(self, data: Dict[str, Any]) -> None:
        """Update the request body data for this client.

        Args:
            data: New data to add or update
        """
        if self.data is None:
            self.data = {}
        self.data.update(data)
        self.logger.debug(f"Updated request data: {data}")
