"""HTTP client package for making API requests.

This package provides a thin wrapper around the requests module.
This package leverages the request functionality to utilize
standard HTTP methods such as GET, POST, PUT, and DELETE and existing methods.
The session provides greater efficiency by using pooled connections and
context management. The extract data lib stores the session and request
information for reuse.


Classes:
    RestClient: Child class of Request and Session.
    - url (str): The base URL for the API.
"""

import logging
import re

from requests import Request, Session, exceptions


class MissingRequestURL(Exception):
    """Exception raised when a request URL is missing."""


class RestClient(Request, Session):
    """RestClient is a child class of Request and Session."""

    def __enter__(self) -> "RestClient":  # Type annotation
        """Enter the context manager and return the client."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the session when the context manager exits."""
        if exc_type is not None:
            # Log the exception details
            logging.error(
                "Exception occurred: %s: %s: %s",
                exc_type.__name__,
                exc_val,
                exc_tb,
            )
        self.close()

    VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}

    def __init__(self, url: str, method: str = "GET", endpoint: str = ""):
        """Initialize the API client with a URL and headers.

        Args:
            url (str): The base URL for the API.
            method (str): The HTTP method to use. Defaults to "GET".
            endpoint (str): The API endpoint. Defaults to an empty string.

        Raises:
            MissingRequestURL: If url is an empty string.
            ValueError: If method is not a valid HTTP method or url is invalid.
        """
        Request.__init__(self)
        Session.__init__(self)

        if url == "" or url is None:
            raise MissingRequestURL("Base URL is missing")
        else:
            self.url = url.strip("/")

        if not re.match(r"^https?://", url):
            raise ValueError("Base URL must start with http:// or https://")

        if method.upper() not in self.VALID_METHODS:
            raise ValueError(
                f"Invalid HTTP method. Must be one of {self.VALID_METHODS}"
            )
        else:
            self.method = method.upper()

        if endpoint != "" or endpoint is not None:
            self.endpoint = endpoint.lstrip("/")
        else:
            self.endpoint = ""

        # Initialize session objects
        self.session = Session()

    def handle_request(self):
        def wrapper(*args, **kwargs):
            """Wrapper function to handle request exceptions and logging."""

            try:
                response = self(*args, **kwargs)
                response.raise_for_status()
                return response
            except exceptions.RequestException as e:
                logging.error(f"Request failed: {str(e)}")
                raise
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                raise

        return wrapper

    @handle_request
    def make_request(self, **kwargs):
        """Make a REST request with specified parameters.

        Args:
            method (str): HTTP method (GET, POST, etc.)
            endpoint (str): API endpoint to call
            **kwargs: Additional request parameters (headers, json, params, etc.)
        """
        self.req = Request(self.method, f"{self.url}/{self.endpoint}", **kwargs)
        prepared = self.session.prepare_request(self.req)
        return self.session.send(prepared)
