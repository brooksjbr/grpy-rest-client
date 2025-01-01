from abc import ABC, abstractmethod
from importlib.metadata import version


class RestClientBase(ABC):
    """Abstract base class defining the interface for REST clients."""

    VALID_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"}
    DEFAULT_TIMEOUT = 60

    @staticmethod
    def get_version() -> str:
        try:
            return version("grpy")
        except Exception:
            return "unknown"

    DEFAULT_USER_AGENT = f"grpy-rest-client/{get_version.__func__()}"

    DEFAULT_HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": DEFAULT_USER_AGENT,
    }

    @abstractmethod
    def __aenter__(self):
        """Enter the context manager."""
        raise NotImplementedError("__enter__ must be implemented by subclass")

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager."""
        raise NotImplementedError("__aexit__ must be implemented by subclass")

    def _validate_http_method(self, method: str) -> None:
        if method.upper() not in self.VALID_METHODS:
            raise ValueError(f"Invalid HTTP method: {method}")

    def _validate_timeout(self, timeout: [int, float]) -> None:
        """Validate timeout is a positive number."""
        if timeout is not None:
            if not isinstance(timeout, (int, float)):
                raise ValueError("Timeout must be a number")
            if timeout <= 0:
                raise ValueError("Timeout must be greater than 0")

    @abstractmethod
    def update_headers(self, headers: dict[str, str]) -> None:
        """Set headers for the request."""
        raise NotImplementedError("set_headers must be implemented by subclass")

    @abstractmethod
    def handle_exception(func):
        """Handle HTTP requests and exceptions."""
        raise NotImplementedError(
            "handle_request must be implemented by subclass"
        )

    @abstractmethod
    def handle_request(self, **kwargs):
        """Make a REST request with specified parameters."""
        raise NotImplementedError("fetch must be implemented by subclass")
