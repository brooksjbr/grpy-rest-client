from asyncio import TimeoutError
from typing import Any, AsyncContextManager, ClassVar, Dict, Optional, Set
from urllib.parse import urljoin

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout
from aiohttp import ContentTypeError as AiohttpContentTypeError
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
                if response.status == 401:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=401,
                        message=f"Authentication required: {error_text}",
                    )
                elif response.status == 403:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=403,
                        message=f"Access forbidden: {error_text}",
                    )
                elif response.status == 404:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=404,
                        message=f"Resource not found: {error_text}",
                    )
                elif response.status == 429:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=429,
                        message=f"Rate limit exceeded: {error_text}",
                    )
                else:
                    raise ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"Client error: {error_text}",
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
            raise ValueError(f"Timeout must be a positive number, got {timeout}")
        return timeout

    async def __aenter__(self):
        """Async context manager entry point."""
        if self.session is None:
            self.session = ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit point."""
        if self.session and not self.session.closed:
            await self.session.close()

    @handle_exception
    async def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        request_url = urljoin(self.url, self.endpoint) if self.endpoint else self.url
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

    async def paginate(self, data_key=None, max_pages=None, request_kwargs=None):
        """
        Paginate through API results.

        Args:
            data_key (str, optional): The key in the response that contains the data items.
            max_pages (int, optional): Maximum number of pages to retrieve.
            request_kwargs (dict, optional): Additional kwargs to pass to handle_request.

        Yields:
            list: The data items from each page.
        """
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

            # Extract the data from the response
            if data_key is not None:
                data_items = response_json.get(data_key, [])
            else:
                data_items = response_json

            # Yield the data items from this page
            yield data_items

            # Increment the page count
            page_count += 1

            # Determine if there are more pages and what the next page parameters should be
            has_more, next_params = self._get_next_page_info(response_json, current_params)

            if not has_more:
                break

            # Update the parameters for the next page
            current_params = next_params

    def _extract_page_data(
        self,
        response_json: Dict[str, Any],
        extract_data_key: Optional[str] = None,
    ):
        """Extract the relevant data from a page response.

        Args:
            response_json: The JSON response from the API
            extract_data_key: Path to the data to extract (e.g., '_embedded.events')

        Returns:
            The extracted data or the full response
        """
        if not extract_data_key:
            return response_json

        # Handle nested keys with dot notation (e.g., '_embedded.events')
        keys = extract_data_key.split(".")
        data = response_json

        for key in keys:
            if key in data:
                data = data[key]
            else:
                # If key doesn't exist, return the full response
                return response_json

        return data

    def _get_next_page_info(self, response_json, current_params):
        """
        Determine if there are more pages and what the next page parameters should be.

        Handles different pagination patterns:
        1. Page number/totalPages structure
        2. _links.next structure (HATEOAS style)

        Args:
            response_json: The JSON response from the API
            current_params: The current request parameters

        Returns:
            Tuple[bool, dict]: A tuple containing:
                - has_more: Boolean indicating if there are more pages
                - next_params: Dictionary of parameters for the next page request
        """
        # Create a copy of the current parameters to modify
        next_params = current_params.copy()

        # Check for HATEOAS-style _links.next structure
        if "_links" in response_json and "next" in response_json["_links"]:
            # Extract the next page URL from the HATEOAS link
            next_href = response_json["_links"]["next"].get("href", "")

            # If there's a next link, there are more pages
            has_more = bool(next_href)

            if has_more and "page=" in next_href:
                # Extract the page number from the URL
                page_param = next_href.split("page=")[1].split("&")[0]
                next_params["page"] = page_param  # Keep as string as it comes from URL

            return has_more, next_params

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

            # There are more pages if the current page is less than total pages
            has_more = int(effective_current_page) < total_pages

            # If there are more pages, update the page parameter for the next request
            if has_more:
                next_params["page"] = int(effective_current_page) + 1

        return has_more, next_params

    def _update_params_from_links(
        self, next_link: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract pagination parameters from a HATEOAS-style 'next' link.

        Args:
            next_link: The 'next' link object from the response
            current_params: Current pagination parameters

        Returns:
            Updated pagination parameters
        """
        # Handle Ticketmaster-style links which may contain a 'href' with query parameters
        if "href" in next_link:
            from urllib.parse import parse_qs, urlparse

            # Parse the URL to extract query parameters
            parsed_url = urlparse(next_link["href"])
            query_params = parse_qs(parsed_url.query)

            # Convert query params (which are lists) to single values
            next_params = current_params.copy()
            for key, value_list in query_params.items():
                if value_list:  # Only update if there's a value
                    next_params[key] = value_list[0]

            return next_params

        return current_params
