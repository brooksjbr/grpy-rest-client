"""Retry manager for handling request retries with different policies."""

import asyncio
import random
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type, TypeVar

from .logging import DefaultLogger, Logger

# Type variable for the return type of the retried function
T = TypeVar("T")


class RetryPolicy:
    """
    Base class for retry policies with default implementation.

    This class provides a default retry behavior that can be used as-is or
    extended by subclasses for more specific retry strategies.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_codes: List[int] = None,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            retry_codes: HTTP status codes that should trigger a retry
            logger: Optional logger instance
        """
        self.max_retries = max_retries
        self.retry_codes = retry_codes or [408, 429, 500, 502, 503, 504]
        self.logger = logger or DefaultLogger(name="grpy-retry")

    def set_logger(self, logger: Logger) -> None:
        """
        Set a new logger for this retry policy.

        Args:
            logger: The logger to use
        """
        self.logger = logger

    def should_retry(
        self, attempt: int, status: Optional[int], exception: Optional[Exception] = None
    ) -> bool:
        """
        Determine if a request should be retried.

        Args:
            attempt: Current attempt number (0-based)
            status: HTTP status code from the response, if available
            exception: Exception that occurred, if any

        Returns:
            True if the request should be retried, False otherwise
        """
        # Don't retry if we've reached the maximum attempts
        if attempt >= self.max_retries:
            return False

        # Retry on specific status codes
        if status is not None and status in self.retry_codes:
            self.logger.debug(f"Will retry due to status code {status}")
            return True

        # Retry on connection-related exceptions
        if exception is not None:
            exception_name = type(exception).__name__
            if any(
                name in exception_name
                for name in ["Timeout", "Connection", "ConnectionError", "ClientError"]
            ):
                self.logger.debug(f"Will retry due to exception: {exception_name}")
                return True

        return False

    async def wait_before_retry(self, attempt: int) -> None:
        """
        Wait before the next retry attempt.

        Args:
            attempt: Current attempt number (0-based)
        """
        # Simple exponential backoff as default behavior
        delay = 2**attempt
        self.logger.info(f"Retrying in {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    async def execute_with_retry(
        self, func: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: The async function to execute with retry logic
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution

        Raises:
            The last exception encountered if all retries fail
        """
        self.logger.debug(f"Starting execution with retry for {func.__name__}")

        last_exception = None
        attempt = 0

        while True:
            try:
                self.logger.debug(f"Executing attempt {attempt + 1}/{self.max_retries + 1}")
                result = await func(*args, **kwargs)

                # Check if the result has a status attribute (like aiohttp.ClientResponse)
                status = getattr(result, "status", None)
                if status is not None:
                    self.logger.debug(f"Received response with status code: {status}")

                    if self.should_retry(attempt, status):
                        self.logger.warning(
                            f"Received retryable status code {status} on attempt {attempt + 1}"
                        )
                        # Create a generic exception for the status code
                        last_exception = Exception(f"HTTP {status}")
                    else:
                        self.logger.info(f"Request succeeded with status code {status}")
                        return result
                else:
                    # If no status, assume success
                    self.logger.info(f"Function {func.__name__} executed successfully")
                    return result

            except Exception as e:
                last_exception = e
                self.logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries + 1} failed: {str(e)}"
                )

                if not self.should_retry(attempt, None, e):
                    self.logger.error(f"Not retrying after exception: {str(e)}")
                    raise

            # If we get here, we need to retry
            if attempt >= self.max_retries:
                self.logger.error(f"All {self.max_retries + 1} retry attempts failed")
                if last_exception:
                    raise last_exception
                else:
                    raise RuntimeError("Retry failed for unknown reason")

            # Wait before retrying
            await self.wait_before_retry(attempt)
            attempt += 1


class ExponentialBackoffRetryPolicy(RetryPolicy):
    """
    Retry policy with exponential backoff.

    This strategy implements exponential backoff with optional jitter for retrying
    failed operations, which helps prevent the "thundering herd" problem.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_codes: List[int] = None,
        initial_delay: float = 0.5,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the exponential backoff retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            retry_codes: HTTP status codes that should trigger a retry
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Factor by which the delay increases
            jitter: Whether to add randomness to the delay
            logger: Optional logger instance
        """
        super().__init__(max_retries, retry_codes, logger)
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    async def wait_before_retry(self, attempt: int) -> None:
        """
        Wait with exponential backoff before retry.

        Args:
            attempt: Current attempt number (0-based)
        """
        delay = min(self.max_delay, self.initial_delay * (self.backoff_factor**attempt))

        if self.jitter:
            # Add jitter by multiplying by a random value between 0.5 and 1.5
            jitter_factor = 0.5 + random.random()
            delay *= jitter_factor
            self.logger.debug(f"Applied jitter factor {jitter_factor:.2f} to delay")

        self.logger.info(f"Retrying in {delay:.2f} seconds...")
        await asyncio.sleep(delay)


class FixedDelayRetryPolicy(RetryPolicy):
    """
    Retry policy with fixed delay between attempts.

    This policy waits for a fixed amount of time between retry attempts.
    """

    def __init__(
        self,
        max_retries: int = 3,
        retry_codes: List[int] = None,
        delay: float = 2.0,
        logger: Optional[Logger] = None,
    ):
        """
        Initialize the fixed delay retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            retry_codes: HTTP status codes that should trigger a retry
            delay: Fixed delay in seconds between retry attempts
            logger: Optional logger instance
        """
        super().__init__(max_retries, retry_codes, logger)
        self.delay = delay

    async def wait_before_retry(self, attempt: int) -> None:
        """
        Wait with fixed delay before retry.

        Args:
            attempt: Current attempt number (0-based)
        """
        self.logger.info(f"Retrying in {self.delay:.2f} seconds...")
        await asyncio.sleep(self.delay)


class RetryManager:
    """Manager for retry policies."""

    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialize the retry manager.

        Args:
            logger: Optional logger instance for logging events
        """
        self._policies: Dict[str, Type[RetryPolicy]] = {}
        self._default_policy: Optional[str] = None
        self.logger = logger or DefaultLogger(name="retry-manager")

    def register_policy(self, name: str, policy_cls: Type[RetryPolicy]) -> None:
        """
        Register a retry policy.

        Args:
            name: Name to register the policy under
            policy_cls: The policy class to register

        Raises:
            TypeError: If policy_cls is not a subclass of RetryPolicy
        """
        if not isinstance(policy_cls, type) or not issubclass(policy_cls, RetryPolicy):
            raise TypeError(f"Expected a RetryPolicy subclass, got {policy_cls}")

        self._policies[name] = policy_cls
        if self.logger:
            self.logger.debug(f"Registered retry policy: {name}")

    def unregister_policy(self, name: str) -> None:
        """
        Unregister a retry policy.

        Args:
            name: Name of the policy to unregister

        Raises:
            KeyError: If the policy is not registered
        """
        if name not in self._policies:
            raise KeyError(f"Policy '{name}' not registered")

        del self._policies[name]

        # If we removed the default policy, clear the default
        if self._default_policy == name:
            self._default_policy = None
            if self.logger:
                self.logger.debug(f"Cleared default policy (was: {name})")

        if self.logger:
            self.logger.debug(f"Unregistered retry policy: {name}")

    def set_default_policy(self, name: str) -> None:
        """
        Set the default retry policy.

        Args:
            name: Name of the policy to set as default

        Raises:
            ValueError: If the policy is not registered
        """
        if name not in self._policies:
            raise ValueError(f"Policy '{name}' not registered")

        self._default_policy = name
        if self.logger:
            self.logger.debug(f"Set default retry policy to: {name}")

    def get_policy(self, name: Optional[str] = None, **kwargs) -> RetryPolicy:
        """
        Get a retry policy instance.

        Args:
            name: Name of the policy to get, or None to use the default
            **kwargs: Additional arguments to pass to the policy constructor

        Returns:
            An instance of the requested retry policy

        Raises:
            ValueError: If no name is provided and no default is set, or if the
                       requested policy is not registered
        """
        if name is None:
            if self._default_policy is None:
                raise ValueError("No default policy set")
            name = self._default_policy

        if name not in self._policies:
            raise ValueError(f"Policy '{name}' not registered")

        policy_cls = self._policies[name]

        # Pass the logger to the policy if one is available
        if self.logger and "logger" not in kwargs:
            kwargs["logger"] = self.logger

        return policy_cls(**kwargs)

    def list_policies(self) -> Dict[str, Type[RetryPolicy]]:
        """
        Get a dictionary of all registered policies.

        Returns:
            A dictionary mapping policy names to policy classes
        """
        return self._policies.copy()

    def get_default_policy_name(self) -> Optional[str]:
        """
        Get the name of the default policy.

        Returns:
            The name of the default policy, or None if no default is set
        """
        return self._default_policy

    def register_builtin_policies(self) -> None:
        """
        Register the built-in retry policies.

        This method registers the standard retry policies included with the library.
        """
        self.register_policy("exponential_backoff", ExponentialBackoffRetryPolicy)
        self.register_policy("fixed_delay", FixedDelayRetryPolicy)

        # Set exponential backoff as the default if no default is set
        if self._default_policy is None:
            self.set_default_policy("exponential_backoff")
