"""
Unit tests for RequestClient class
"""

from abc import ABC, abstractmethod


class TestRestClientBase(ABC):
    """
    Test cases for core client functionality.

    Tests the basic operations of the client including:
    - Initialization
    """

    @abstractmethod
    def client(self):
        """Setup fixture for RequestClient initialization"""

    @abstractmethod
    def mock(self):
        """Setup fixture for requests_mock."""
