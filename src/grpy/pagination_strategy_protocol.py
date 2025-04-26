from typing import Any, Dict, Protocol, Tuple, runtime_checkable


@runtime_checkable
class PaginationStrategy(Protocol):
    """Protocol defining the interface for pagination strategies."""

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
        ...

    def extract_items(self, response: Dict[str, Any]) -> list:
        """
        Extract the actual items from a paginated response.

        Args:
            response: The response data

        Returns:
            List of items from the response
        """
        ...
