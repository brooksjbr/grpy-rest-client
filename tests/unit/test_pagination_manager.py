from typing import Any, Dict, List, Tuple
from unittest.mock import MagicMock

import pytest

from src.grpy.pagination_manager import PaginationManager
from src.grpy.pagination_strategy_protocol import PaginationStrategy


# Define test strategy classes
class TestPageNumberStrategy:
    """Test implementation of page number pagination strategy."""

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        page_info = response.get("page", {})
        current_page = page_info.get("number", 0)
        total_pages = page_info.get("totalPages", 0)

        has_more = current_page + 1 < total_pages

        next_params = current_params.copy()
        if has_more:
            next_params["page"] = current_page + 1

        return has_more, next_params

    def extract_items(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        return response.get("items", [])


class TestHateoasStrategy:
    """Test implementation of HATEOAS pagination strategy."""

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        links = response.get("_links", {})
        has_next = "next" in links

        next_params = current_params.copy()
        return has_next, next_params

    def extract_items(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        embedded = response.get("_embedded", {})
        return embedded.get("events", [])


class InvalidStrategy:
    """A class that doesn't implement the PaginationStrategy protocol."""

    def some_other_method(self):
        pass


@pytest.fixture
def logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def manager(logger):
    """Create a pagination manager with a mock logger."""
    return PaginationManager(logger=logger)


def test_register_strategy(manager, logger):
    """Test registering a strategy."""
    manager.register_strategy("test_page", TestPageNumberStrategy)

    # Verify the strategy was registered
    assert "test_page" in manager.list_strategies()
    assert manager.list_strategies()["test_page"] == TestPageNumberStrategy

    # Verify logging occurred
    logger.debug.assert_called_with("Registered pagination strategy: test_page")


def test_register_invalid_strategy(manager):
    """Test that registering an invalid strategy raises an error."""
    with pytest.raises(TypeError, match="does not implement the PaginationStrategy protocol"):
        manager.register_strategy("invalid", InvalidStrategy)


def test_register_non_class(manager):
    """Test that registering a non-class raises an error."""
    with pytest.raises(TypeError, match="Expected a class"):
        manager.register_strategy("not_a_class", "string_value")


def test_unregister_strategy(manager, logger):
    """Test unregistering a strategy."""
    # Register a strategy first
    manager.register_strategy("test_page", TestPageNumberStrategy)
    assert "test_page" in manager.list_strategies()

    # Unregister it
    manager.unregister_strategy("test_page")

    # Verify it was removed
    assert "test_page" not in manager.list_strategies()

    # Verify logging occurred
    logger.debug.assert_called_with("Unregistered pagination strategy: test_page")


def test_unregister_nonexistent_strategy(manager):
    """Test that unregistering a non-existent strategy raises an error."""
    with pytest.raises(KeyError, match="Strategy 'nonexistent' not registered"):
        manager.unregister_strategy("nonexistent")


def test_set_default_strategy(manager, logger):
    """Test setting the default strategy."""
    # Register strategies
    manager.register_strategy("test_page", TestPageNumberStrategy)
    manager.register_strategy("test_hateoas", TestHateoasStrategy)

    # Set default
    manager.set_default_strategy("test_page")

    # Verify default was set
    assert manager.get_default_strategy_name() == "test_page"

    # Verify logging occurred
    logger.debug.assert_called_with("Set default pagination strategy to: test_page")


def test_set_nonexistent_default_strategy(manager):
    """Test that setting a non-existent strategy as default raises an error."""
    with pytest.raises(ValueError, match="Strategy 'nonexistent' not registered"):
        manager.set_default_strategy("nonexistent")


def test_get_strategy_by_name(manager):
    """Test getting a strategy by name."""
    # Register a strategy
    manager.register_strategy("test_page", TestPageNumberStrategy)

    # Get the strategy
    strategy = manager.get_strategy("test_page")

    # Verify it's the correct type
    assert isinstance(strategy, TestPageNumberStrategy)
    assert isinstance(strategy, PaginationStrategy)


def test_get_default_strategy(manager):
    """Test getting the default strategy."""
    # Register strategies and set default
    manager.register_strategy("test_page", TestPageNumberStrategy)
    manager.register_strategy("test_hateoas", TestHateoasStrategy)
    manager.set_default_strategy("test_hateoas")

    # Get the default strategy
    strategy = manager.get_strategy()

    # Verify it's the correct type
    assert isinstance(strategy, TestHateoasStrategy)


def test_get_strategy_no_default(manager):
    """Test that getting the default strategy when none is set raises an error."""
    with pytest.raises(ValueError, match="No default strategy set"):
        manager.get_strategy()


def test_get_nonexistent_strategy(manager):
    """Test that getting a non-existent strategy raises an error."""
    with pytest.raises(ValueError, match="Strategy 'nonexistent' not registered"):
        manager.get_strategy("nonexistent")


def test_unregister_default_strategy(manager):
    """Test that unregistering the default strategy clears the default."""
    # Register strategies and set default
    manager.register_strategy("test_page", TestPageNumberStrategy)
    manager.set_default_strategy("test_page")

    # Verify default is set
    assert manager.get_default_strategy_name() == "test_page"

    # Unregister the default
    manager.unregister_strategy("test_page")

    # Verify default was cleared
    assert manager.get_default_strategy_name() is None


def test_register_builtin_strategies(manager):
    """Test registering built-in strategies."""
    # Register built-ins
    manager.register_builtin_strategies()

    # Verify the expected strategies are registered
    strategies = manager.list_strategies()
    assert "page_number" in strategies
    assert "hateoas" in strategies

    # Verify default was set to hateoas
    assert manager.get_default_strategy_name() == "hateoas"


def test_strategy_functionality(manager):
    """Test that strategies obtained from the manager work correctly."""
    # Register strategies
    manager.register_strategy("test_page", TestPageNumberStrategy)

    # Get a strategy
    strategy = manager.get_strategy("test_page")

    # Test the strategy's functionality
    response = {"items": [{"id": 1, "name": "Test"}], "page": {"number": 0, "totalPages": 3}}
    current_params = {"page": 0, "size": 10}

    # Test get_next_page_info
    has_more, next_params = strategy.get_next_page_info(response, current_params)
    assert has_more is True
    assert next_params == {"page": 1, "size": 10}

    # Test extract_items
    items = strategy.extract_items(response)
    assert items == [{"id": 1, "name": "Test"}]
