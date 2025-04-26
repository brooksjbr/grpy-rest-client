"""Retry strategies for REST API clients."""

import asyncio
import random
from abc import ABC, abstractmethod
from functools import wraps
from typing import Any, Callable, List, Optional, Type, TypeVar, cast

import aiohttp

from .logging import DefaultLogger, Logger

# Type variable for the return type of the decorated function
T = TypeVar("T")


class RetryStrategy(ABC):
    """Base class for retry strategies.

    This abstract class defines the interface that all retry strategies must implement.
    Different retry strategies can be used for different types of failures.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """Initialize the retry strategy.

        Args:
            logger: Custom logger instance (uses DefaultLogger if None)
        """
        self.logger = logger or DefaultLogger(name="grpy-retry")

    def set_logger(self, logger: Logger) -> None:
        """Set a new logger for this retry strategy.

        Args:
            logger: The logger to use
        """
        self.logger = logger

    @abstractmethod
    async def execute_with_retry(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with retry logic.

        Args:
            func: The function to execute with retry logic
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution
        """
        pass


class ExponentialBackoffRetry(RetryStrategy):
    """Retry strategy with exponential backoff.

    This strategy implements exponential backoff with jitter for retrying
    failed operations, which helps prevent the "thundering herd" problem.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.5,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
        retryable_status_codes: Optional[List[int]] = None,
        logger: Optional[Logger] = None,
    ):
        """Initialize the exponential backoff retry strategy.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Factor by which the delay increases
            jitter: Whether to add randomness to the delay
            retryable_exceptions: List of exception types that should trigger a retry
            retryable_status_codes: List of HTTP status codes that should trigger a retry
        """
        super().__init__(logger=logger)
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            aiohttp.ClientError,
            asyncio.TimeoutError,
            ConnectionError,
        ]
        self.retryable_status_codes = retryable_status_codes or [
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        ]

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate the delay for a retry attempt.

        Args:
            attempt: The current retry attempt (0-based)

        Returns:
            The delay in seconds
        """
        delay = min(self.max_delay, self.initial_delay * (self.backoff_factor**attempt))
        if self.jitter:
            # Add jitter by multiplying by a random value between 0.5 and 1.5
            jitter_factor = 0.5 + random.random()
            delay *= jitter_factor
            self.logger.debug(f"Applied jitter factor {jitter_factor:.2f} to delay")

        self.logger.debug(f"Calculated retry delay: {delay:.2f}s for attempt {attempt}")
        return delay

    async def execute_with_retry(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute a function with exponential backoff retry logic.

        Args:
            func: The function to execute with retry logic
            *args: Positional arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function

        Returns:
            The result of the function execution

        Raises:
            The last exception encountered if all retries fail
        """
        self.logger.debug(f"Starting execution with retry for {func.__name__}")
        self.logger.debug(f"Max retries: {self.max_retries}, Initial delay: {self.initial_delay}s")

        last_exception = None
        attempt = 0

        while attempt <= self.max_retries:
            try:
                self.logger.debug(f"Executing attempt {attempt + 1}/{self.max_retries + 1}")
                result = await func(*args, **kwargs)

                # Check if the result is an aiohttp.ClientResponse
                if isinstance(result, aiohttp.ClientResponse):
                    self.logger.debug(f"Received response with status code: {result.status}")

                    if result.status in self.retryable_status_codes:
                        self.logger.warning(
                            f"Received retryable status code {result.status} on attempt {attempt + 1}"
                        )
                        last_exception = aiohttp.ClientResponseError(
                            request_info=result.request_info,
                            history=result.history,
                            status=result.status,
                            message=f"HTTP {result.status}",
                        )
                    else:
                        self.logger.info(f"Request succeeded with status code {result.status}")
                        return result
                else:
                    self.logger.info(f"Function {func.__name__} executed successfully")
                    return result

            except tuple(self.retryable_exceptions) as e:
                last_exception = e
                self.logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries + 1} failed: {str(e)}"
                )

            # If this was the last attempt, raise the exception
            if attempt == self.max_retries:
                self.logger.error(f"All {self.max_retries + 1} retry attempts failed")
                break

            # Calculate delay for the next retry
            delay = self._calculate_delay(attempt)
            self.logger.info(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
            attempt += 1

        # If we've exhausted all retries, raise the last exception
        if last_exception:
            self.logger.error(
                f"All {self.max_retries + 1} retry attempts failed: {str(last_exception)}"
            )
            raise last_exception

        # This should never happen if the function always returns or raises
        error_msg = "Unexpected state in retry logic"
        self.logger.critical(error_msg)
        raise RuntimeError(error_msg)


def with_retry(
    retry_strategy: Optional[RetryStrategy] = None,
    max_retries: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: Optional[List[Type[Exception]]] = None,
    retryable_status_codes: Optional[List[int]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic to a function.

    Args:
        retry_strategy: The retry strategy to use
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Factor by which the delay increases
        jitter: Whether to add randomness to the delay
        retryable_exceptions: List of exception types that should trigger a retry
        retryable_status_codes: List of HTTP status codes that should trigger a retry

    Returns:
        A decorator function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal retry_strategy
            if retry_strategy is None:
                retry_strategy = ExponentialBackoffRetry(
                    max_retries=max_retries,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    backoff_factor=backoff_factor,
                    jitter=jitter,
                    retryable_exceptions=retryable_exceptions,
                    retryable_status_codes=retryable_status_codes,
                )
            return await retry_strategy.execute_with_retry(func, *args, **kwargs)

        return cast(Callable[..., T], wrapper)

    return decorator
