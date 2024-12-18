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

from requests import Request, Session


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

    def __init__(self, url: str, method: str = "GET"):
        """Initialize the API client with a URL and headers.

        Args:
            url (str): The base URL for the API.
            method (str): The HTTP method to use. Defaults to "GET".

        Raises:
            MissingRequestURL: If url is an empty string.
            ValueError: If method is not a valid HTTP method or url is invalid.
        """
        Request.__init__(self)
        Session.__init__(self)

        if url == "":
            raise MissingRequestURL("Base URL is missing")

        if not re.match(r"^https?://", url):
            raise ValueError("Base URL must start with http:// or https://")

        if method.upper() not in self.VALID_METHODS:
            raise ValueError(
                f"Invalid HTTP method. Must be one of {self.VALID_METHODS}"
            )

        # Initialize the request and session objects
        self.req = Request(method, url)
        self.url = self.req.url
        self.method = self.req.method
        self.session = Session()
        self.init_request = self.session.prepare_request(self.req)

    def send_request(self):
        """Send an HTTP request and return the response."""
        return self.session.send(self.init_request)
