import asyncio
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.grpy.logging import Logger
from src.grpy.retry_manager import (
    ExponentialBackoffRetryPolicy,
    FixedDelayRetryPolicy,
    RetryManager,
    RetryPolicy,
)


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status: int = 200, data: Optional[Dict[str, Any]] = None):
        self.status = status
        self.data = data or {}


@pytest.fixture
def logger():
    """Create a mock logger for testing."""
    return MagicMock(spec=Logger)


@pytest.fixture
def retry_manager(logger):
    """Create a RetryManager with a mock logger."""
    return RetryManager(logger=logger)


class TestRetryPolicy:
    """Tests for the RetryPolicy base class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.retry_codes == [408, 429, 500, 502, 503, 504]

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        policy = RetryPolicy(max_retries=5, retry_codes=[400, 401])
        assert policy.max_retries == 5
        assert policy.retry_codes == [400, 401]

    def test_set_logger(self, logger):
        """Test setting a logger."""
        policy = RetryPolicy()
        policy.set_logger(logger)
        assert policy.logger == logger

    def test_should_retry_status_code(self):
        """Test should_retry with retryable status code."""
        policy = RetryPolicy(max_retries=2, retry_codes=[500])

        # Should retry on first attempt with retryable status
        assert policy.should_retry(0, 500) is True

        # Should retry on second attempt with retryable status
        assert policy.should_retry(1, 500) is True

        # Should not retry after max_retries
        assert policy.should_retry(2, 500) is False

        # Should not retry on non-retryable status
        assert policy.should_retry(0, 404) is False

    def test_should_retry_exception(self):
        """Test should_retry with exceptions."""
        policy = RetryPolicy(max_retries=2)

        # Should retry on connection errors
        assert policy.should_retry(0, None, ConnectionError("Connection refused")) is True

        # Should retry on timeout errors
        assert policy.should_retry(0, None, asyncio.TimeoutError()) is True

        # Should not retry on other exceptions
        assert policy.should_retry(0, None, ValueError("Invalid value")) is False

        # Should not retry after max_retries
        assert policy.should_retry(2, None, ConnectionError("Connection refused")) is False

    @pytest.mark.asyncio
    async def test_wait_before_retry(self, logger):
        """Test wait_before_retry method."""
        policy = RetryPolicy(logger=logger)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await policy.wait_before_retry(0)
            mock_sleep.assert_called_once_with(1)  # 2^0 = 1

            mock_sleep.reset_mock()
            await policy.wait_before_retry(1)
            mock_sleep.assert_called_once_with(2)  # 2^1 = 2

            mock_sleep.reset_mock()
            await policy.wait_before_retry(2)
            mock_sleep.assert_called_once_with(4)  # 2^2 = 4

    @pytest.mark.asyncio
    async def test_execute_with_retry_success(self, logger):
        """Test execute_with_retry with successful execution."""
        policy = RetryPolicy(logger=logger)
        mock_func = AsyncMock(return_value="success")

        result = await policy.execute_with_retry(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        mock_func.assert_called_once_with("arg1", kwarg1="value1")

    @pytest.mark.asyncio
    async def test_execute_with_retry_http_response(self, logger):
        """Test execute_with_retry with HTTP response."""
        policy = RetryPolicy(logger=logger)
        mock_response = MockResponse(status=200)
        mock_func = AsyncMock(return_value=mock_response)

        result = await policy.execute_with_retry(mock_func)

        assert result == mock_response
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_with_retry_retryable_status(self, logger):
        """Test execute_with_retry with retryable status code."""
        policy = RetryPolicy(max_retries=2, logger=logger)

        # First call returns a 500 status, second call succeeds
        responses = [MockResponse(status=500), MockResponse(status=200)]
        mock_func = AsyncMock(side_effect=lambda: responses.pop(0))

        with patch.object(policy, "wait_before_retry", new_callable=AsyncMock) as mock_wait:
            result = await policy.execute_with_retry(mock_func)

            assert result.status == 200
            assert mock_func.call_count == 2
            mock_wait.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_execute_with_retry_exception(self, logger):
        """Test execute_with_retry with retryable exception."""
        policy = RetryPolicy(max_retries=2, logger=logger)

        # First call raises an exception, second call succeeds
        mock_func = AsyncMock(side_effect=[ConnectionError("Connection refused"), "success"])

        with patch.object(policy, "wait_before_retry", new_callable=AsyncMock) as mock_wait:
            result = await policy.execute_with_retry(mock_func)

            assert result == "success"
            assert mock_func.call_count == 2
            mock_wait.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_execute_with_retry_max_attempts(self, logger):
        """Test execute_with_retry with maximum retry attempts."""
        policy = RetryPolicy(max_retries=2, logger=logger)

        # Create a response with a retryable status code
        mock_response = MockResponse(status=500)

        # Mock the function to always return a response with status 500
        mock_func = AsyncMock(return_value=mock_response)

        # Don't mock should_retry - let the real method run
        # The real should_retry will return True for the first two attempts (0 and 1)
        # and False for the third attempt (2) because attempt >= max_retries

        with patch.object(policy, "wait_before_retry", new_callable=AsyncMock) as mock_wait:
            # The implementation should return the last response after max retries
            result = await policy.execute_with_retry(mock_func)

            # Verify the function was called the expected number of times
            assert mock_func.call_count == 3  # Initial + 2 retries
            assert mock_wait.call_count == 2

            # Check that the result is the last response
            assert result == mock_response
            assert result.status == 500


class TestExponentialBackoffRetryPolicy:
    """Tests for the ExponentialBackoffRetryPolicy class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        policy = ExponentialBackoffRetryPolicy()
        assert policy.max_retries == 3
        assert policy.initial_delay == 0.5
        assert policy.max_delay == 30.0
        assert policy.backoff_factor == 2.0
        assert policy.jitter is True

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        policy = ExponentialBackoffRetryPolicy(
            max_retries=5,
            retry_codes=[400, 401],
            initial_delay=1.0,
            max_delay=10.0,
            backoff_factor=3.0,
            jitter=False,
        )
        assert policy.max_retries == 5
        assert policy.retry_codes == [400, 401]
        assert policy.initial_delay == 1.0
        assert policy.max_delay == 10.0
        assert policy.backoff_factor == 3.0
        assert policy.jitter is False

    @pytest.mark.asyncio
    async def test_wait_before_retry_no_jitter(self, logger):
        """Test wait_before_retry without jitter."""
        policy = ExponentialBackoffRetryPolicy(
            initial_delay=1.0, backoff_factor=2.0, jitter=False, logger=logger
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await policy.wait_before_retry(0)
            mock_sleep.assert_called_once_with(1.0)  # initial_delay * (backoff_factor^0)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(1)
            mock_sleep.assert_called_once_with(2.0)  # initial_delay * (backoff_factor^1)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(2)
            mock_sleep.assert_called_once_with(4.0)  # initial_delay * (backoff_factor^2)

    @pytest.mark.asyncio
    async def test_wait_before_retry_with_jitter(self, logger):
        """Test wait_before_retry with jitter."""
        policy = ExponentialBackoffRetryPolicy(
            initial_delay=1.0, backoff_factor=2.0, jitter=True, logger=logger
        )

        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch("random.random", return_value=0.5),
        ):  # jitter_factor = 0.5 + 0.5 = 1.0
            await policy.wait_before_retry(0)
            mock_sleep.assert_called_once_with(
                1.0
            )  # initial_delay * (backoff_factor^0) * jitter_factor

            mock_sleep.reset_mock()
            await policy.wait_before_retry(1)
            mock_sleep.assert_called_once_with(
                2.0
            )  # initial_delay * (backoff_factor^1) * jitter_factor

            mock_sleep.reset_mock()
            await policy.wait_before_retry(2)
            mock_sleep.assert_called_once_with(
                4.0
            )  # initial_delay * (backoff_factor^2) * jitter_factor

    @pytest.mark.asyncio
    async def test_wait_before_retry_max_delay(self, logger):
        """Test wait_before_retry respects max_delay."""
        policy = ExponentialBackoffRetryPolicy(
            initial_delay=1.0, max_delay=3.0, backoff_factor=2.0, jitter=False, logger=logger
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await policy.wait_before_retry(0)
            mock_sleep.assert_called_once_with(1.0)  # initial_delay * (backoff_factor^0)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(1)
            mock_sleep.assert_called_once_with(2.0)  # initial_delay * (backoff_factor^1)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(2)
            mock_sleep.assert_called_once_with(3.0)  # Capped at max_delay


class TestFixedDelayRetryPolicy:
    """Tests for the FixedDelayRetryPolicy class."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        policy = FixedDelayRetryPolicy()
        assert policy.max_retries == 3
        assert policy.delay == 2.0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        policy = FixedDelayRetryPolicy(max_retries=5, retry_codes=[400, 401], delay=3.5)
        assert policy.max_retries == 5
        assert policy.retry_codes == [400, 401]
        assert policy.delay == 3.5

    @pytest.mark.asyncio
    async def test_wait_before_retry(self, logger):
        """Test wait_before_retry method."""
        policy = FixedDelayRetryPolicy(delay=2.5, logger=logger)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await policy.wait_before_retry(0)
            mock_sleep.assert_called_once_with(2.5)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(1)
            mock_sleep.assert_called_once_with(2.5)

            mock_sleep.reset_mock()
            await policy.wait_before_retry(2)
            mock_sleep.assert_called_once_with(2.5)


class TestRetryManager:
    """Tests for the RetryManager class."""

    def test_init(self, logger):
        """Test initialization."""
        manager = RetryManager(logger=logger)
        assert manager.logger == logger
        assert manager._policies == {}
        assert manager._default_policy is None

    def test_register_policy(self, retry_manager, logger):
        """Test registering a policy."""
        retry_manager.register_policy("fixed", FixedDelayRetryPolicy)

        assert "fixed" in retry_manager._policies
        assert retry_manager._policies["fixed"] == FixedDelayRetryPolicy
        logger.debug.assert_called_with("Registered retry policy: fixed")

    def test_register_invalid_policy(self, retry_manager):
        """Test registering an invalid policy."""
        with pytest.raises(TypeError, match="Expected a RetryPolicy subclass"):
            retry_manager.register_policy("invalid", str)

    def test_unregister_policy(self, retry_manager, logger):
        """Test unregistering a policy."""
        # Register a policy first
        retry_manager.register_policy("fixed", FixedDelayRetryPolicy)
        assert "fixed" in retry_manager._policies

        # Unregister it
        retry_manager.unregister_policy("fixed")

        assert "fixed" not in retry_manager._policies
        logger.debug.assert_called_with("Unregistered retry policy: fixed")

    def test_unregister_default_policy(self, retry_manager, logger):
        """Test unregistering the default policy."""
        # Register a policy and set as default
        retry_manager.register_policy("fixed", FixedDelayRetryPolicy)
        retry_manager.set_default_policy("fixed")  # Corrected method name

        assert retry_manager.get_default_policy_name() == "fixed"

        # Unregister it
        retry_manager.unregister_policy("fixed")

        # Verify default was cleared
        assert retry_manager.get_default_policy_name() is None
        logger.debug.assert_any_call("Cleared default policy (was: fixed)")
