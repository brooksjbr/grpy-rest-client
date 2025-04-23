"""Unit tests for pagination strategies with retry functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from grpy.pagination import (
    HateoasPaginationStrategy,
    PageNumberPaginationStrategy,
    PaginationStrategy,
)
from grpy.retry import ExponentialBackoffRetry


# Create a concrete subclass of PaginationStrategy for testing
class MockPaginationStrategy(PaginationStrategy):
    """Concrete implementation of PaginationStrategy for testing."""

    def extract_data(self, response_json, data_key=None):
        return response_json

    def get_next_page_info(self, response_json, current_params):
        return False, {}


class TestPaginationStrategyRetry:
    """Tests for retry functionality in PaginationStrategy."""

    def test_pagination_strategy_init_with_defaults(self):
        """Test that PaginationStrategy initializes retry strategy with defaults."""
        strategy = MockPaginationStrategy()
        assert isinstance(strategy.retry_strategy, ExponentialBackoffRetry)
        assert strategy.retry_strategy.max_retries == 3
        assert strategy.retry_strategy.initial_delay == 0.5
        assert strategy.retry_strategy.max_delay == 30.0
        assert strategy.retry_strategy.backoff_factor == 2.0
        assert strategy.retry_strategy.jitter is True

    def test_pagination_strategy_init_with_custom_retry(self):
        """Test that PaginationStrategy accepts custom retry strategy."""
        custom_retry = ExponentialBackoffRetry(
            max_retries=5, initial_delay=1.0, max_delay=60.0, backoff_factor=3.0, jitter=False
        )

        strategy = MockPaginationStrategy(retry_strategy=custom_retry)
        assert strategy.retry_strategy is custom_retry

    @pytest.mark.asyncio
    async def test_execute_with_retry_delegates_to_retry_strategy(self):
        """Test that execute_with_retry delegates to the retry strategy."""
        # Create a mock retry strategy
        mock_retry_strategy = MagicMock(spec=ExponentialBackoffRetry)
        mock_retry_strategy.execute_with_retry = AsyncMock(return_value="test result")

        # Create the pagination strategy with the mock retry strategy
        strategy = MockPaginationStrategy(retry_strategy=mock_retry_strategy)

        # Create a mock function to execute
        mock_func = AsyncMock(return_value="direct result")

        # Execute the function with retry
        result = await strategy.execute_with_retry(mock_func, "arg1", kwarg1="value1")

        # Verify the result and that the retry strategy was called correctly
        assert result == "test result"
        mock_retry_strategy.execute_with_retry.assert_called_once_with(
            mock_func, "arg1", kwarg1="value1"
        )


class TestPageNumberPaginationStrategyRetry:
    """Tests for retry functionality in PageNumberPaginationStrategy."""

    @pytest.mark.asyncio
    async def test_page_number_strategy_with_retry_success(self):
        """Test PageNumberPaginationStrategy with successful retry."""
        # Create a mock function that fails once then succeeds
        mock_func = AsyncMock(
            side_effect=[
                aiohttp.ClientError("Network error"),
                {"page": {"number": 0, "totalPages": 3}, "items": ["item1", "item2"]},
            ]
        )

        # Create the strategy with fast retry settings for testing
        strategy = PageNumberPaginationStrategy(max_retries=2, initial_delay=0.01, jitter=False)

        # Execute with retry
        result = await strategy.execute_with_retry(mock_func)

        # Verify the result
        assert result["page"]["number"] == 0
        assert result["items"] == ["item1", "item2"]
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_page_number_strategy_with_retry_failure(self):
        """Test PageNumberPaginationStrategy with failed retries."""
        # Create a mock function that always fails
        error = aiohttp.ClientError("Persistent network error")
        mock_func = AsyncMock(side_effect=error)

        # Create the strategy with fast retry settings for testing
        strategy = PageNumberPaginationStrategy(max_retries=1, initial_delay=0.01, jitter=False)

        # Execute with retry and expect failure
        with pytest.raises(aiohttp.ClientError) as excinfo:
            await strategy.execute_with_retry(mock_func)

        assert str(excinfo.value) == "Persistent network error"
        assert mock_func.call_count == 2  # Initial attempt + 1 retry


class TestHateoasPaginationStrategyRetry:
    """Tests for retry functionality in HateoasPaginationStrategy."""

    @pytest.mark.asyncio
    async def test_hateoas_strategy_with_retry_success(self):
        """Test HateoasPaginationStrategy with successful retry."""
        # Create a mock function that fails once then succeeds
        mock_func = AsyncMock(
            side_effect=[
                asyncio.TimeoutError("Request timed out"),
                {
                    "_links": {"next": {"href": "https://api.example.com/items?page=2"}},
                    "items": ["item1", "item2"],
                },
            ]
        )

        # Create the strategy with fast retry settings for testing
        strategy = HateoasPaginationStrategy(max_retries=2, initial_delay=0.01, jitter=False)

        # Execute with retry
        result = await strategy.execute_with_retry(mock_func)

        # Verify the result
        assert "_links" in result
        assert "next" in result["_links"]
        assert result["items"] == ["item1", "item2"]
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_hateoas_strategy_with_retryable_status_code(self):
        """Test HateoasPaginationStrategy with retryable status code."""
        # Create mock responses
        mock_response_503 = MagicMock(spec=aiohttp.ClientResponse)
        mock_response_503.status = 503
        mock_response_503.request_info = MagicMock()
        mock_response_503.history = ()

        success_response = {
            "_links": {
                "self": {"href": "https://api.example.com/items?page=1"},
                "next": {"href": "https://api.example.com/items?page=2"},
            },
            "items": ["item1", "item2"],
        }

        # Create a mock function that returns a 503 response then succeeds
        mock_func = AsyncMock(side_effect=[mock_response_503, success_response])

        # Create the strategy with fast retry settings for testing
        strategy = HateoasPaginationStrategy(max_retries=2, initial_delay=0.01, jitter=False)

        # Execute with retry
        result = await strategy.execute_with_retry(mock_func)

        # Verify the result
        assert result == success_response
        assert mock_func.call_count == 2
