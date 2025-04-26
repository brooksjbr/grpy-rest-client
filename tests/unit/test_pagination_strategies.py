import pytest

from src.grpy.pagination import PageNumberPaginationStrategy


class TestPageNumberPaginationStrategy:
    @pytest.fixture
    def strategy(self, pagination_strategy_factory):
        """Create a PageNumberPaginationStrategy instance for testing."""
        return pagination_strategy_factory(PageNumberPaginationStrategy)

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

    def test_extract_data_simple_key(self, strategy, page_number_response):
        """Test extracting data with a simple key."""
        result = strategy.extract_data(page_number_response, "items")
        assert result == page_number_response["items"]
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

    def test_extract_data_invalid_key(self, strategy, page_number_response):
        """Test extracting data with an invalid key returns the full response."""
        result = strategy.extract_data(page_number_response, "nonexistent")
        assert result == page_number_response

    def test_extract_data_no_key(self, strategy, page_number_response):
        """Test extracting data with no key returns the full response."""
        result = strategy.extract_data(page_number_response, None)
        assert result == page_number_response

    def test_get_next_page_info_has_more_pages(self, strategy, page_number_response):
        """Test getting next page info when there are more pages."""
        current_params = {"page": 0, "size": 2}
        has_more, next_params = strategy.get_next_page_info(page_number_response, current_params)

        assert has_more is True
        assert next_params == {"page": 1, "size": 2}

    def test_get_next_page_info_last_page(self, strategy, last_page_response):
        """Test getting next page info when on the last page."""
        current_params = {"page": 2, "size": 2}
        has_more, next_params = strategy.get_next_page_info(last_page_response, current_params)

        assert has_more is False
        assert next_params == {"page": 2, "size": 2}  # Params unchanged

    def test_get_next_page_info_no_page_param(self, strategy, page_number_response):
        """Test getting next page info when no page param in current params."""
        current_params = {"size": 2}
        has_more, next_params = strategy.get_next_page_info(page_number_response, current_params)

        assert has_more is True
        assert next_params == {"size": 2, "page": 1}  # Page param added

    def test_get_next_page_info_no_page_info(self, strategy):
        """Test getting next page info when response has no page info."""
        response = {"items": [{"id": "item1"}]}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_malformed_page_info_dict(self, strategy):
        """Test handling of malformed page info where 'page' is not a dictionary."""
        # Response with 'page' as a string instead of a dictionary
        response = {"items": [{"id": "item1"}], "page": "invalid"}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_none_page_info(self, strategy):
        """Test handling of None page info."""
        # Response with 'page' as None
        response = {"items": [{"id": "item1"}], "page": None}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_missing_required_fields(self, strategy):
        """Test handling of page info missing required fields."""
        # Response with page info missing number and totalPages
        response = {"items": [{"id": "item1"}], "page": {"size": 10}}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_malformed_page_values(self, strategy):
        """Test handling of page info with malformed values."""
        # Response with non-numeric values for page fields that can be converted to int
        response = {
            "items": [{"id": "item1"}],
            "page": {
                "number": "1",  # This can be converted to int
                "totalPages": "3",  # This can be converted to int
            },
        }
        current_params = {"page": 0}

        # This should not raise an exception
        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is True
        assert next_params == {"page": 1}  # Page incremented

    def test_get_next_page_info_non_convertible_values(self, strategy):
        """Test handling of page info with values that can't be converted to integers."""
        # Response with non-numeric values for page fields
        response = {
            "items": [{"id": "item1"}],
            "page": {
                "number": 0,  # Valid number
                "totalPages": "not-a-number",  # This will cause ValueError during int conversion
            },
        }
        current_params = {"page": 0}

        # We need to modify the implementation to handle this case
        has_more, next_params = strategy.get_next_page_info(response, current_params)

        # Since we can't properly compare, pagination should stop
        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged
