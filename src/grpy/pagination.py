"""Pagination strategies for REST API clients."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Type

from .retry import ExponentialBackoffRetry, RetryStrategy


class PaginationStrategy(ABC):
    """Base class for pagination strategies.

    This abstract class defines the interface that all pagination strategies must implement.
    Different APIs use different pagination mechanisms (page numbers, cursors, HATEOAS links),
    and this strategy pattern allows for pluggable pagination handling.
    """

    def __init__(
        self,
        retry_strategy: Optional[RetryStrategy] = None,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        retryable_status_codes: Optional[List[int]] = None,
    ):
        """Initialize the pagination strategy with retry configuration.

        Args:
            retry_strategy: Custom retry strategy to use
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Factor by which the delay increases
            jitter: Whether to add randomness to the delay
            retryable_exceptions: List of exception types that should trigger a retry
            retryable_status_codes: List of HTTP status codes that should trigger a retry
        """
        self.retry_strategy = retry_strategy or ExponentialBackoffRetry(
            max_retries=max_retries,
            initial_delay=initial_delay,
            max_delay=max_delay,
            backoff_factor=backoff_factor,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            retryable_status_codes=retryable_status_codes,
        )

    @abstractmethod
    def extract_data(self, response_json: Dict[str, Any], data_key: Optional[str] = None) -> Any:
        """Extract data items from the response.

        Args:
            response_json: The JSON response from the API
            data_key: Optional key or path to extract data from (e.g., '_embedded.events')

        Returns:
            The extracted data items
        """
        pass

    @abstractmethod
    def get_next_page_info(
        self, response_json: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Determine if there are more pages and what the next page parameters should be.

        Args:
            response_json: The JSON response from the API
            current_params: The current request parameters

        Returns:
            Tuple containing:
                - Boolean indicating if there are more pages
                - Dictionary of parameters for the next page request
        """
        pass

    async def execute_with_retry(self, func, *args, **kwargs):
        """Execute a function with retry logic.

        Args:
            func: The function to execute
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution
        """
        return await self.retry_strategy.execute_with_retry(func, *args, **kwargs)


class PageNumberPaginationStrategy(PaginationStrategy):
    """Pagination strategy for APIs that use page numbers.

    This strategy handles APIs that use a page number and totalPages structure,
    typically found in APIs that return a "page" object with pagination metadata.
    """

    def extract_data(self, response_json: Dict[str, Any], data_key: Optional[str] = None) -> Any:
        """Extract data from response using the specified data key."""
        if not data_key:
            return response_json

        # Handle nested keys with dot notation (e.g., '_embedded.events')
        keys = data_key.split(".")
        data = response_json

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                # If key doesn't exist, return the full response
                return response_json

        return data

    def get_next_page_info(
        self, response_json: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if there are more pages based on page numbers."""
        next_params = current_params.copy()

        # Extract pagination information from the response
        page_info = response_json.get("page", {})
        current_page = page_info.get("number")
        total_pages = page_info.get("totalPages")

        # Determine if there are more pages based on page numbers
        has_more = False
        if current_page is not None and total_pages is not None:
            # Get the current page from parameters if available
            param_page = current_params.get("page")

            # Use the page from parameters if it exists, otherwise use the one from response
            effective_current_page = param_page if param_page is not None else current_page

            # Convert to integers for comparison (if they're strings)
            if isinstance(effective_current_page, str):
                effective_current_page = int(effective_current_page)
            if isinstance(total_pages, str):
                total_pages = int(total_pages)

            # There are more pages if the current page is less than total pages - 1
            # (since page numbers are 0-indexed in the test data)
            has_more = effective_current_page < total_pages - 1

            # If there are more pages, update the page parameter for the next request
            if has_more:
                next_params["page"] = int(effective_current_page) + 1

        return has_more, next_params


class HateoasPaginationStrategy(PaginationStrategy):
    """Pagination strategy for APIs that use HATEOAS links.

    This strategy handles APIs that follow HATEOAS principles by including
    navigation links in the response, typically in a "_links" object.
    """

    def extract_data(self, response_json: Dict[str, Any], data_key: Optional[str] = None) -> Any:
        """Extract data from response using the specified data key."""
        if not data_key:
            return response_json

        # Handle nested keys with dot notation (e.g., '_embedded.events')
        keys = data_key.split(".")
        data = response_json

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                # If key doesn't exist, return the full response
                return response_json

        return data

    def get_next_page_info(
        self, response_json: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if there are more pages based on HATEOAS links."""
        next_params = current_params.copy()

        # Check for HATEOAS-style _links.next structure
        if "_links" in response_json and "next" in response_json["_links"]:
            # Extract the next page URL from the HATEOAS link
            next_link = response_json["_links"]["next"]
            next_href = next_link.get("href", "")

            # If there's a next link, there are more pages
            has_more = bool(next_href)

            if has_more:
                # Extract parameters from the next link
                from urllib.parse import parse_qs, urlparse

                # Parse the URL to extract query parameters
                parsed_url = urlparse(next_href)
                query_params = parse_qs(parsed_url.query)

                # Convert query params (which are lists) to single values
                for key, value_list in query_params.items():
                    if value_list:  # Only update if there's a value
                        next_params[key] = value_list[0]

            return has_more, next_params

        return False, next_params
