from typing import Any, Dict, Tuple

from src.grpy.pagination_strategy_protocol import PaginationStrategy


class ValidPaginationStrategy:
    """A valid implementation of the PaginationStrategy protocol."""

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get information for the next page."""
        return False, current_params

    def extract_items(self, response: Dict[str, Any]) -> list:
        """Extract items from the response."""
        return response.get("items", [])


class InvalidPaginationStrategy:
    """An invalid implementation missing required methods."""

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Get information for the next page."""
        return False, current_params

    # Missing extract_items method


class WrongSignaturePaginationStrategy:
    """An invalid implementation with wrong method signatures."""

    def get_next_page_info(self, response: Dict[str, Any]) -> bool:
        """Wrong signature - missing current_params and wrong return type."""
        return False

    def extract_items(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Wrong return type - should return list."""
        return {}


class CustomPaginationStrategy:
    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        page = current_params.get("page", 1)
        total_pages = response.get("total_pages", 1)
        has_more = page < total_pages

        next_params = current_params.copy()
        if has_more:
            next_params["page"] = page + 1

        return has_more, next_params

    def extract_items(self, response: Dict[str, Any]) -> list:
        return response.get("data", [])


def test_valid_strategy_implements_protocol():
    """Test that a valid strategy is recognized as implementing the protocol."""
    strategy = ValidPaginationStrategy()
    assert isinstance(strategy, PaginationStrategy)


def test_invalid_strategy_does_not_implement_protocol():
    """Test that an invalid strategy is not recognized as implementing the protocol."""
    strategy = InvalidPaginationStrategy()
    assert not isinstance(strategy, PaginationStrategy)


def test_wrong_signature_strategy():
    """
    Test that a strategy with wrong method signatures is still considered
    to implement the protocol at runtime due to duck typing.

    Note: This is a limitation of runtime_checkable protocols - they only check
    for method existence, not signature compatibility.
    """
    strategy = WrongSignaturePaginationStrategy()
    # This will pass because runtime_checkable only checks method names
    assert isinstance(strategy, PaginationStrategy)


def test_protocol_methods_callable():
    """Test that protocol methods are callable on a valid implementation."""
    strategy = ValidPaginationStrategy()
    response = {"items": [1, 2, 3]}
    current_params = {"page": 1}

    has_more, next_params = strategy.get_next_page_info(response, current_params)
    assert has_more is False
    assert next_params == current_params

    items = strategy.extract_items(response)
    assert items == [1, 2, 3]


def test_custom_strategy_behavior():
    """Test a custom strategy with specific behavior."""

    strategy = CustomPaginationStrategy()
    assert isinstance(strategy, PaginationStrategy)

    # Test with more pages available
    response = {"data": ["item1", "item2"], "total_pages": 3}
    current_params = {"page": 1}

    has_more, next_params = strategy.get_next_page_info(response, current_params)
    assert has_more is True
    assert next_params == {"page": 2}
    assert strategy.extract_items(response) == ["item1", "item2"]

    # Test with last page
    response = {"data": ["item5"], "total_pages": 3}
    current_params = {"page": 3}

    has_more, next_params = strategy.get_next_page_info(response, current_params)
    assert has_more is False
    assert next_params == {"page": 3}
