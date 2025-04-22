import pytest

from src.grpy.pagination import PageNumberPaginationStrategy


class TestPageNumberPaginationStrategy:
    @pytest.fixture
    def strategy(self):
        """Create a PageNumberPaginationStrategy instance for testing."""
        return PageNumberPaginationStrategy()

    @pytest.fixture
    def page_response(self):
        """Sample response with page number pagination."""
        return {
            "items": [
                {"id": "item1", "name": "Item 1"},
                {"id": "item2", "name": "Item 2"},
            ],
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 0,  # First page (0-indexed)
            },
        }

    @pytest.fixture
    def last_page_response(self):
        """Sample response for the last page."""
        return {
            "items": [
                {"id": "item5", "name": "Item 5"},
            ],
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 2,  # Last page (0-indexed)
            },
        }

    @pytest.fixture
    def nested_data_response(self):
        """Sample response with nested data structure."""
        return {
            "_embedded": {
                "events": [
                    {"id": "event1", "name": "Event 1"},
                    {"id": "event2", "name": "Event 2"},
                ]
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 0,
            },
        }

    def test_extract_data_simple_key(self, strategy, page_response):
        """Test extracting data with a simple key."""
        result = strategy.extract_data(page_response, "items")
        assert result == page_response["items"]
        assert len(result) == 2
        assert result[0]["id"] == "item1"
        assert result[1]["id"] == "item2"

    def test_extract_data_nested_key(self, strategy, nested_data_response):
        """Test extracting data with a nested key using dot notation."""
        result = strategy.extract_data(nested_data_response, "_embedded.events")
        assert result == nested_data_response["_embedded"]["events"]
        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[1]["id"] == "event2"

    def test_extract_data_invalid_key(self, strategy, page_response):
        """Test extracting data with an invalid key returns the full response."""
        result = strategy.extract_data(page_response, "nonexistent")
        assert result == page_response

    def test_extract_data_no_key(self, strategy, page_response):
        """Test extracting data with no key returns the full response."""
        result = strategy.extract_data(page_response, None)
        assert result == page_response

    def test_get_next_page_info_has_more_pages(self, strategy, page_response):
        """Test getting next page info when there are more pages."""
        current_params = {"page": 0, "size": 2}
        has_more, next_params = strategy.get_next_page_info(page_response, current_params)

        assert has_more is True
        assert next_params == {"page": 1, "size": 2}

    def test_get_next_page_info_last_page(self, strategy, last_page_response):
        """Test getting next page info when on the last page."""
        current_params = {"page": 2, "size": 2}
        has_more, next_params = strategy.get_next_page_info(last_page_response, current_params)

        assert has_more is False
        assert next_params == {"page": 2, "size": 2}  # Params unchanged

    def test_get_next_page_info_no_page_param(self, strategy, page_response):
        """Test getting next page info when no page param in current params."""
        current_params = {"size": 2}
        has_more, next_params = strategy.get_next_page_info(page_response, current_params)

        assert has_more is True
        assert next_params == {"size": 2, "page": 1}  # Page param added

    def test_get_next_page_info_no_page_info(self, strategy):
        """Test getting next page info when response has no page info."""
        response = {"items": [{"id": "item1"}]}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged
