import pytest

from src.grpy.pagination import HateoasPaginationStrategy


class TestHateoasPaginationStrategy:
    @pytest.fixture
    def strategy(self):
        """Create a HateoasPaginationStrategy instance for testing."""
        return HateoasPaginationStrategy()

    @pytest.fixture
    def hateoas_page1_response(self):
        """Sample response for first page with HATEOAS links."""
        return {
            "_embedded": {
                "events": [
                    {"id": "event1", "name": "Concert 1"},
                    {"id": "event2", "name": "Concert 2"},
                ]
            },
            "_links": {
                "self": {"href": "/events?page=0&size=2"},
                "next": {"href": "/events?page=1&size=2"},
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 0,
            },
        }

    @pytest.fixture
    def hateoas_page2_response(self):
        """Sample response for middle page with HATEOAS links."""
        return {
            "_embedded": {
                "events": [
                    {"id": "event3", "name": "Concert 3"},
                    {"id": "event4", "name": "Concert 4"},
                ]
            },
            "_links": {
                "self": {"href": "/events?page=1&size=2"},
                "next": {"href": "/events?page=2&size=2"},
                "prev": {"href": "/events?page=0&size=2"},
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 1,
            },
        }

    @pytest.fixture
    def hateoas_last_page_response(self):
        """Sample response for last page with HATEOAS links."""
        return {
            "_embedded": {
                "events": [
                    {"id": "event5", "name": "Concert 5"},
                ]
            },
            "_links": {
                "self": {"href": "/events?page=2&size=2"},
                "prev": {"href": "/events?page=1&size=2"},
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 2,
            },
        }

    @pytest.fixture
    def hateoas_with_query_params_response(self):
        """Sample response with additional query parameters in links."""
        return {
            "_embedded": {
                "events": [
                    {"id": "event1", "name": "Concert 1"},
                    {"id": "event2", "name": "Concert 2"},
                ]
            },
            "_links": {
                "self": {"href": "/events?keyword=music&page=0&size=2"},
                "next": {"href": "/events?keyword=music&page=1&size=2"},
            },
        }

    def test_extract_data_simple_key(self, strategy, hateoas_page1_response):
        """Test extracting data with a simple key."""
        result = strategy.extract_data(hateoas_page1_response, "_embedded")
        assert result == hateoas_page1_response["_embedded"]
        assert "events" in result
        assert len(result["events"]) == 2

    def test_extract_data_nested_key(self, strategy, hateoas_page1_response):
        """Test extracting data with a nested key using dot notation."""
        result = strategy.extract_data(hateoas_page1_response, "_embedded.events")
        assert result == hateoas_page1_response["_embedded"]["events"]
        assert len(result) == 2
        assert result[0]["id"] == "event1"
        assert result[1]["id"] == "event2"

    def test_extract_data_invalid_key(self, strategy, hateoas_page1_response):
        """Test extracting data with an invalid key returns the full response."""
        result = strategy.extract_data(hateoas_page1_response, "nonexistent")
        assert result == hateoas_page1_response

    def test_extract_data_no_key(self, strategy, hateoas_page1_response):
        """Test extracting data with no key returns the full response."""
        result = strategy.extract_data(hateoas_page1_response, None)
        assert result == hateoas_page1_response

    def test_get_next_page_info_has_more_pages(self, strategy, hateoas_page1_response):
        """Test getting next page info when there are more pages."""
        current_params = {"page": 0, "size": 2}
        has_more, next_params = strategy.get_next_page_info(hateoas_page1_response, current_params)

        assert has_more is True
        assert next_params == {"page": "1", "size": "2"}  # Values from URL are strings

    def test_get_next_page_info_middle_page(self, strategy, hateoas_page2_response):
        """Test getting next page info from a middle page."""
        current_params = {"page": 1, "size": 2}
        has_more, next_params = strategy.get_next_page_info(hateoas_page2_response, current_params)

        assert has_more is True
        assert next_params == {"page": "2", "size": "2"}

    def test_get_next_page_info_last_page(self, strategy, hateoas_last_page_response):
        """Test getting next page info when on the last page."""
        current_params = {"page": 2, "size": 2}
        has_more, next_params = strategy.get_next_page_info(
            hateoas_last_page_response, current_params
        )

        assert has_more is False
        assert next_params == {"page": 2, "size": 2}  # Params unchanged

    def test_get_next_page_info_with_additional_params(
        self, strategy, hateoas_with_query_params_response
    ):
        """Test getting next page info with additional query parameters."""
        current_params = {"page": 0, "size": 2, "keyword": "music"}
        has_more, next_params = strategy.get_next_page_info(
            hateoas_with_query_params_response, current_params
        )

        assert has_more is True
        assert next_params == {"page": "1", "size": "2", "keyword": "music"}
        assert next_params["keyword"] == "music"  # Original param preserved

    def test_get_next_page_info_no_links(self, strategy):
        """Test getting next page info when response has no _links."""
        response = {"items": [{"id": "item1"}]}
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged

    def test_get_next_page_info_empty_next_link(self, strategy):
        """Test getting next page info when _links exists but next is empty."""
        response = {
            "items": [{"id": "item1"}],
            "_links": {"self": {"href": "/events?page=0"}, "next": {}},  # Empty next link
        }
        current_params = {"page": 0}

        has_more, next_params = strategy.get_next_page_info(response, current_params)

        assert has_more is False
        assert next_params == {"page": 0}  # Params unchanged
