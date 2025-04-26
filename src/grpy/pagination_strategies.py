"""
Pagination strategies for handling different pagination formats in API responses.
"""

from typing import Any, Dict, List, Tuple


class PageNumberPaginationStrategy:
    """
    Strategy for page number based pagination.

    This strategy handles APIs that use page numbers for pagination, typically
    with parameters like 'page' and 'size'.
    """

    def __init__(self, zero_indexed: bool = True):
        """
        Initialize the page number pagination strategy.

        Args:
            zero_indexed: Whether page numbering starts at 0 (True) or 1 (False)
        """
        self.zero_indexed = zero_indexed

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract pagination information from response and determine next page parameters.

        Args:
            response: The response data from the previous request
            current_params: The parameters used in the previous request

        Returns:
            Tuple containing:
                - Boolean indicating if there are more pages
                - Dict with parameters for the next page request
        """
        page_info = response.get("page", {})
        current_page = page_info.get("number", 0)
        total_pages = page_info.get("totalPages", 0)

        # Adjust for 1-indexed pagination if needed
        if not self.zero_indexed:
            current_page_adjusted = current_page
        else:
            current_page_adjusted = current_page + 1

        has_more = current_page_adjusted < total_pages

        next_params = current_params.copy()
        if has_more:
            next_params["page"] = current_page + 1

        return has_more, next_params

    def extract_items(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract the actual items from a paginated response.

        Args:
            response: The response data

        Returns:
            List of items from the response
        """
        return response.get("items", [])


class HateoasPaginationStrategy:
    """
    Strategy for HATEOAS-based pagination.

    This strategy handles APIs that follow HATEOAS (Hypermedia as the Engine of
    Application State) principles, where links to next/previous pages are included
    in the response.
    """

    def get_next_page_info(
        self, response: Dict[str, Any], current_params: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Extract pagination information from response and determine next page parameters.

        Args:
            response: The response data from the previous request
            current_params: The parameters used in the previous request

        Returns:
            Tuple containing:
                - Boolean indicating if there are more pages
                - Dict with parameters for the next page request
        """
        links = response.get("_links", {})
        has_next = "next" in links

        if not has_next:
            return False, current_params

        # Extract query parameters from the next link
        next_link = links["next"].get("href", "")
        next_params = current_params.copy()

        # Parse the query string if present
        if "?" in next_link:
            query_string = next_link.split("?")[1]
            for param in query_string.split("&"):
                if "=" in param:
                    key, value = param.split("=", 1)
                    # Try to convert numeric values
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                    next_params[key] = value

        return True, next_params

    def extract_items(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract the actual items from a paginated response.

        Args:
            response: The response data

        Returns:
            List of items from the response
        """
        embedded = response.get("_embedded", {})
        # Look for common collection names
        for key in embedded:
            if isinstance(embedded[key], list):
                return embedded[key]

        # If no collections found, return empty list
        return []
