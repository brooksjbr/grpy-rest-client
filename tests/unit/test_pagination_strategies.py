import pytest

from src.grpy.pagination import PageNumberPaginationStrategy


class TestPageNumberPaginationStrategy:
    @pytest.fixture
    def zero_indexed_strategy(self, pagination_strategy_factory):
        """Create a PageNumberPaginationStrategy instance with 0-indexed pagination for testing."""
        return pagination_strategy_factory(
            PageNumberPaginationStrategy, page_index_starts_at_zero=True
        )

    @pytest.fixture
    def one_indexed_strategy(self, pagination_strategy_factory):
        """Create a PageNumberPaginationStrategy instance with 1-indexed pagination for testing."""
        return pagination_strategy_factory(
            PageNumberPaginationStrategy, page_index_starts_at_zero=False
        )

    @pytest.fixture
    def custom_param_strategy(self, pagination_strategy_factory):
        """Create a PageNumberPaginationStrategy instance with custom page parameter name."""
        return pagination_strategy_factory(
            PageNumberPaginationStrategy, page_param_name="pageNumber"
        )

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
    def one_indexed_page_response(self):
        """Sample response with 1-indexed page number pagination."""
        return {
            "items": [
                {"id": "item1", "name": "Item 1"},
                {"id": "item2", "name": "Item 2"},
            ],
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 1,  # First page (1-indexed)
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
    def one_indexed_last_page_response(self):
        """Sample response for the last page with 1-indexed pagination."""
        return {
            "items": [
                {"id": "item5", "name": "Item 5"},
            ],
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 3,  # Last page (1-indexed)
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

    def test_extract_data_simple_key(self, zero_indexed_strategy, page_response):
        """Test extracting data with a simple key."""
        result = zero_indexed_strategy.extract_data(page_response, "items")
        assert result == page_response["items"]
        assert len(result) == 2
        assert result[0]["id"] == "item1"
        assert result[1]["id"] == "item2"

    def test_extract_data_nested_key(self, zero_indexed_strategy, nested_data_response):
        """Test extracting data with a nested key using dot notation."""
        result = zero_indexed_strategy.extract_data(nested_data_response, "_embedded.events")
        assert result == nested_data_response["_embedded"]["events"]
        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[1]["id"] == "event2"

    def test_extract_data_invalid_key(self, zero_indexed_strategy, page_response):
        """Test extracting data with an invalid key returns the full response."""
        result = zero_indexed_strategy.extract_data(page_response, "nonexistent")
        assert result == page_response

    def test_extract_data_no_key(self, zero_indexed_strategy, page_response):
        """Test extracting data with no key returns the full response."""
        result = zero_indexed_strategy.extract_data(page_response, None)
        assert result == page_response

    def test_get_next_page_info_has_more_pages_zero_indexed(
        self, zero_indexed_strategy, page_response
    ):
        """Test getting next page info when there are more pages with 0-indexed pagination."""
        current_params = {"page": 0, "size": 2}
        has_more, next_params = zero_indexed_strategy.get_next_page_info(
            page_response, current_params
        )

        assert has_more is True
        assert next_params == {"page": 1, "size": 2}

    def test_get_next_page_info_has_more_pages_one_indexed(
        self, one_indexed_strategy, one_indexed_page_response
    ):
        """Test getting next page info when there are more pages with 1-indexed pagination."""
        current_params = {"page": 1, "size": 2}
        has_more, next_params = one_indexed_strategy.get_next_page_info(
            one_indexed_page_response, current_params
        )

        assert has_more is True
        assert next_params == {"page": 2, "size": 2}

    def test_get_next_page_info_last_page_zero_indexed(
        self, zero_indexed_strategy, last_page_response
    ):
        """Test getting next page info when on the last page with 0-indexed pagination."""
        current_params = {"page": 2, "size": 2}
        has_more, next_params = zero_indexed_strategy.get_next_page_info(
            last_page_response, current_params
        )

        assert has_more is False
        assert next_params == {"page": 2, "size": 2}  # Params unchanged

    def test_get_next_page_info_last_page_one_indexed(
        self, one_indexed_strategy, one_indexed_last_page_response
    ):
        """Test getting next page info when on the last page with 1-indexed pagination."""
        current_params = {"page": 3, "size": 2}
        has_more, next_params = one_indexed_strategy.get_next_page_info(
            one_indexed_last_page_response, current_params
        )

        assert has_more is False
        assert next_params == {"page": 3, "size": 2}  # Params unchanged

    def test_get_next_page_info_no_page_param(self, zero_indexed_strategy, page_response):
        """Test getting next page info when no page param in current params."""
        current_params = {"size": 2}
        has_more, next_params = zero_indexed_strategy.get_next_page_info(
            page_response, current_params
        )

        assert has_more is True
        assert next_params == {"size": 2, "page": 1}  # Page param added

    def test_get_next_page_info_custom_page_param(self, custom_param_strategy, page_response):
        """Test getting next page info with custom page parameter name."""
        current_params = {"pageNumber": 0, "size": 2}
        has_more, next_params = custom_param_strategy.get_next_page_info(
            page_response, current_params
        )

        assert has_more is True
        assert next_params == {"pageNumber": 1, "size": 2}  # Custom page param incremented

    def test_get_next_page_info_no_page_info(self, zero_indexed_strategy):
        """Test getting next page info when response has no page info."""
        response = {"items": [{"id": "item1"}]}
        current_params = {"page": 0}

        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_malformed_page_info_dict(self, zero_indexed_strategy):
        """Test handling of malformed page info where 'page' is not a dictionary."""
        # Response with 'page' as a string instead of a dictionary
        response = {"items": [{"id": "item1"}], "page": "invalid"}
        current_params = {"page": 0}

        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_none_page_info(self, zero_indexed_strategy):
        """Test handling of None page info."""
        # Response with 'page' as None
        response = {"items": [{"id": "item1"}], "page": None}
        current_params = {"page": 0}

        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_missing_required_fields(self, zero_indexed_strategy):
        """Test handling of page info missing required fields."""
        # Response with page info missing number and totalPages
        response = {"items": [{"id": "item1"}], "page": {"size": 10}}
        current_params = {"page": 0}

        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_malformed_page_values(self, zero_indexed_strategy):
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
        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        assert has_more is True
        assert next_params == {"page": 1}  # Page incremented

    def test_get_next_page_info_non_convertible_values(self, zero_indexed_strategy):
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
        has_more, next_params = zero_indexed_strategy.get_next_page_info(response, current_params)

        # Since we can't properly compare, pagination should stop
        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged
