"""Example usage of the RestClient class."""

from grpy.rest_client import RestClient

SAMPLE_URL = "https://jsonplaceholder.typicode.com/todos/1"


def simple_client_request():
    """Example usage of the RestClient without context manager"""
    client = RestClient(SAMPLE_URL)
    resp = client.send_request()
    print(resp.json())


def simple_client_request_context_manager():
    """Example usage of the RestClient with context manager"""
    with RestClient(SAMPLE_URL) as client:
        resp = client.send_request()
        print(resp.json())


def main():
    """Main function to run the examples."""
    simple_client_request()
    simple_client_request_context_manager()


if __name__ == "__main__":
    main()
