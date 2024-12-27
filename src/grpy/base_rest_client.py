from abc import ABC, abstractmethod


class BaseRestClient(ABC):
    """Abstract base class defining the interface for REST clients."""

    VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}

    @abstractmethod
    def __aenter__(self):
        """Enter the context manager."""
        raise NotImplementedError("__enter__ must be implemented by subclass")

    @abstractmethod
    def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        raise NotImplementedError("__exit__ must be implemented by subclass")

    @abstractmethod
    def update_headers(self, headers: dict):
        """Set headers for the request."""
        raise NotImplementedError("set_headers must be implemented by subclass")

    @abstractmethod
    def handle_exception(self):
        """Handle HTTP requests and exceptions."""
        raise NotImplementedError(
            "handle_request must be implemented by subclass"
        )

    @abstractmethod
    def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        raise NotImplementedError("fetch must be implemented by subclass")
