"""Pagination manager for managing and providing pagination strategies."""

from typing import Dict, Optional, Type

from .logging import DefaultLogger, Logger
from .pagination_strategy_protocol import PaginationStrategy


class PaginationManager:
    """
    Manager for pagination strategies.

    This class provides a central registry for pagination strategies and handles
    their registration, configuration, and instantiation.
    """

    def __init__(self, logger: Optional[Logger] = None):
        """
        Initialize the pagination manager.

        Args:
            logger: Optional logger instance for logging events
        """
        self._strategies: Dict[str, Type[PaginationStrategy]] = {}
        self._default_strategy: Optional[str] = None
        self.logger = logger or DefaultLogger(name="pagination-manager")

    def register_strategy(self, name: str, strategy_cls: Type[PaginationStrategy]) -> None:
        """
        Register a pagination strategy.

        Args:
            name: Name to register the strategy under
            strategy_cls: The strategy class to register
        """
        if not isinstance(strategy_cls, type):
            raise TypeError(f"Expected a class, got {type(strategy_cls)}")

        # Verify the class implements the PaginationStrategy protocol
        # This is a runtime check that ensures the class has the required methods
        dummy_instance = strategy_cls()
        if not isinstance(dummy_instance, PaginationStrategy):
            raise TypeError(
                f"Class {strategy_cls.__name__} does not implement the PaginationStrategy protocol"
            )

        self._strategies[name] = strategy_cls
        self.logger.debug(f"Registered pagination strategy: {name}")

    def unregister_strategy(self, name: str) -> None:
        """
        Unregister a pagination strategy.

        Args:
            name: Name of the strategy to unregister

        Raises:
            KeyError: If the strategy is not registered
        """
        if name not in self._strategies:
            raise KeyError(f"Strategy '{name}' not registered")

        del self._strategies[name]

        # If we removed the default strategy, clear the default
        if self._default_strategy == name:
            self._default_strategy = None
            self.logger.debug(f"Cleared default strategy (was: {name})")

        self.logger.debug(f"Unregistered pagination strategy: {name}")

    def set_default_strategy(self, name: str) -> None:
        """
        Set the default pagination strategy.

        Args:
            name: Name of the strategy to set as default

        Raises:
            ValueError: If the strategy is not registered
        """
        if name not in self._strategies:
            raise ValueError(f"Strategy '{name}' not registered")

        self._default_strategy = name
        self.logger.debug(f"Set default pagination strategy to: {name}")

    def get_strategy(self, name: Optional[str] = None) -> PaginationStrategy:
        """
        Get a pagination strategy instance.

        Args:
            name: Name of the strategy to get, or None to use the default

        Returns:
            An instance of the requested pagination strategy

        Raises:
            ValueError: If no name is provided and no default is set, or if the
                       requested strategy is not registered
        """
        if name is None:
            if self._default_strategy is None:
                raise ValueError("No default strategy set")
            name = self._default_strategy

        if name not in self._strategies:
            raise ValueError(f"Strategy '{name}' not registered")

        strategy_cls = self._strategies[name]
        return strategy_cls()

    def list_strategies(self) -> Dict[str, Type[PaginationStrategy]]:
        """
        Get a dictionary of all registered strategies.

        Returns:
            A dictionary mapping strategy names to strategy classes
        """
        return self._strategies.copy()

    def get_default_strategy_name(self) -> Optional[str]:
        """
        Get the name of the default strategy.

        Returns:
            The name of the default strategy, or None if no default is set
        """
        return self._default_strategy

    def register_builtin_strategies(self) -> None:
        """
        Register the built-in pagination strategies.

        This method imports and registers the standard pagination strategies
        included with the library.
        """
        # Import here to avoid circular imports
        from .pagination_strategies import HateoasPaginationStrategy, PageNumberPaginationStrategy

        self.register_strategy("page_number", PageNumberPaginationStrategy)
        self.register_strategy("hateoas", HateoasPaginationStrategy)

        # Set HATEOAS as the default if no default is set
        if self._default_strategy is None:
            self.set_default_strategy("hateoas")
