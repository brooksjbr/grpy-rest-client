"""
Pagination strategies for handling different pagination formats in API responses.
"""

from typing import Any, Dict, List, Optional, Tuple


class PageNumberPaginationStrategy:
    """
    Strategy for page number based pagination.

    This strategy handles APIs that use page numbers for pagination, typically
    with parameters like 'page' and 'size'.
    """

    def __init__(self, page_index_starts_at_zero: bool = True, page_param_name: str = "page"):
        """
        Initialize the page number pagination strategy.

        Args:
            page_index_starts_at_zero: Whether page numbering starts at 0 (True) or 1 (False)
            page_param_name: The name of the page parameter used in requests
        """
        self.zero_indexed = page_index_starts_at_zero
        self.page_param_name = page_param_name

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
        if not isinstance(page_info, dict) or page_info is None:
            return False, current_params.copy()

        try:
            current_page = int(page_info.get("number", 0))
            total_pages = int(page_info.get("totalPages", 0))
        except (ValueError, TypeError):
            # If conversion fails, assume no more pages
            return False, current_params.copy()

        # Adjust for 1-indexed pagination if needed
        if not self.zero_indexed:
            current_page_adjusted = current_page
        else:
            current_page_adjusted = current_page + 1

        has_more = current_page_adjusted < total_pages

        next_params = current_params.copy()
        page_param = self.page_param_name  # Use the configured page parameter name

        if has_more:
            # Use the current_params page value for incrementing, not the response page value
            current_param_page = next_params.get(page_param, 0)
            next_params[page_param] = current_param_page + 1

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

    def extract_data(self, response: Dict[str, Any], key_path: Optional[str]) -> Any:
        """
        Extract data from a response using a key path.

        Args:
            response: The response data
            key_path: Dot-separated path to the data (e.g., "_embedded.events")
                     If None, returns the full response

        Returns:
            The extracted data or the full response if key_path is None
        """
        if key_path is None:
            return response

        # Handle dot notation for nested keys
        keys = key_path.split(".")
        data = response

        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                # If key doesn't exist, return the full response
                return response

        return data


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
