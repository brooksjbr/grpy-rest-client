import pytest


class TestPagination:
    @pytest.fixture
    def ticketmaster_page1_response(self):
        """Mock response for first page of Ticketmaster API"""
        return {
            "_links": {
                "self": {"href": "/events?page=0&size=2"},
                "next": {"href": "/events?page=1&size=2"},
            },
            "_embedded": {
                "events": [
                    {"id": "event1", "name": "Concert 1"},
                    {"id": "event2", "name": "Concert 2"},
                ]
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 0,
            },
        }

    @pytest.fixture
    def ticketmaster_page2_response(self):
        """Mock response for second page of Ticketmaster API"""
        return {
            "_links": {
                "self": {"href": "/events?page=1&size=2"},
                "next": {"href": "/events?page=2&size=2"},
                "prev": {"href": "/events?page=0&size=2"},
            },
            "_embedded": {
                "events": [
                    {"id": "event3", "name": "Concert 3"},
                    {"id": "event4", "name": "Concert 4"},
                ]
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 1,
            },
        }

    @pytest.fixture
    def ticketmaster_page3_response(self):
        """Mock response for last page of Ticketmaster API"""
        return {
            "_links": {
                "self": {"href": "/events?page=2&size=2"},
                "prev": {"href": "/events?page=1&size=2"},
            },
            "_embedded": {
                "events": [
                    {"id": "event5", "name": "Concert 5"},
                ]
            },
            "page": {
                "size": 2,
                "totalElements": 5,
                "totalPages": 3,
                "number": 2,
            },
        }

    @pytest.mark.asyncio
    async def test_extract_page_data_with_simple_key(self, client_fixture):
        """Test extracting data with a simple key"""

        response_json = {"items": [{"id": 1}, {"id": 2}]}

        result = client_fixture._extract_page_data(response_json, "items")

        assert result == [{"id": 1}, {"id": 2}]

    @pytest.mark.asyncio
    async def test_extract_page_data_with_nested_key(self, client_fixture):
        """Test extracting data with a nested key path"""

        response_json = {"_embedded": {"events": [{"id": "e1"}, {"id": "e2"}]}}

        result = client_fixture._extract_page_data(response_json, "_embedded.events")

        assert result == [{"id": "e1"}, {"id": "e2"}]

    @pytest.mark.asyncio
    async def test_extract_page_data_with_missing_key(self, client_fixture):
        """Test extracting data with a key that doesn't exist"""

        response_json = {"data": [{"id": 1}]}

        result = client_fixture._extract_page_data(response_json, "items")

        # Should return the full response if key doesn't exist
        assert result == response_json

    @pytest.mark.asyncio
    async def test_extract_page_data_without_key(self, client_fixture):
        """Test extracting data without specifying a key"""

        response_json = {"data": [{"id": 1}]}

        result = client_fixture._extract_page_data(response_json, None)

        # Should return the full response if no key is specified
        assert result == response_json

    @pytest.mark.asyncio
    async def test_update_params_from_links(self, client_fixture):
        """Test extracting pagination parameters from HATEOAS links"""

        next_link = {"href": "/events?page=2&size=20&sort=date,asc"}
        current_params = {"page": 1, "size": 20}

        result = client_fixture._update_params_from_links(next_link, current_params)

        assert result["page"] == "2"  # Note: will be string from URL parsing
        assert result["size"] == "20"
        assert result["sort"] == "date,asc"

    @pytest.mark.asyncio
    async def test_update_params_from_links_without_href(self, client_fixture):
        """Test handling links without href attribute"""

        next_link = {"rel": "next"}  # No href
        current_params = {"page": 1}

        result = client_fixture._update_params_from_links(next_link, current_params)

        # Should return unchanged params if no href
        assert result == current_params

    @pytest.mark.asyncio
    async def test_get_next_page_info_with_links(self, client_fixture):
        """Test determining next page with _links.next structure"""
        response_json = {"_links": {"next": {"href": "/events?page=2"}}}
        current_params = {"page": 1}

        has_more, next_params = client_fixture._get_next_page_info(response_json, current_params)
        assert has_more is True
        assert next_params["page"] == "2"

    @pytest.mark.asyncio
    async def test_get_next_page_info_with_page_info(self, client_fixture):
        """Test determining next page with page object structure"""

        response_json = {"page": {"number": 1, "totalPages": 3}}
        current_params = {"page": 1}

        has_more, next_params = client_fixture._get_next_page_info(response_json, current_params)

        assert has_more is True
        assert next_params["page"] == 2  # Should be incremented

    @pytest.mark.asyncio
    async def test_get_next_page_info_last_page(self, client_fixture):
        """Test determining next page when on the last page"""

        response_json = {"page": {"number": 2, "totalPages": 3}}
        current_params = {"page": 2}

        has_more, next_params = client_fixture._get_next_page_info(response_json, current_params)

        assert has_more is True
        assert next_params["page"] == 3

    @pytest.mark.asyncio
    async def test_get_next_page_info_no_more_pages(self, client_fixture):
        """Test determining next page when there are no more pages"""

        response_json = {"page": {"number": 2, "totalPages": 3}}
        current_params = {"page": 3}  # Already at last page + 1

        has_more, next_params = client_fixture._get_next_page_info(response_json, current_params)

        assert has_more is False
        assert next_params == current_params
