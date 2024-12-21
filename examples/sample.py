"""Example usage of the RestClient class."""

from grpy.rest_client import RestClient

""" RestClient using with context manager utilizing connection pooling """
with RestClient("https://jsonplaceholder.typicode.com") as client:
    # GET request
    client.endpoint = "/todos/1"
    response = client.make_request()
    print(response.json())

    # POST request
    client.endpoint = "/users"
    client.method = "POST"
    client.headers = {"Content-type": "application/json; charset=UTF-8"}
    response = client.make_request(
        json={"name": "John Doe"},
    )
    print(response.json())
