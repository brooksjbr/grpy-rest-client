import asyncio

from grpy.async_rest_client import AsyncRestClient

BASE_URL = "https://jsonplaceholder.typicode.com"
ENDPOINT = "/todos/1"


async def main():
    async with AsyncRestClient(BASE_URL, endpoint=ENDPOINT) as client:
        response = await client.handle_request()
        json_response = await response.json()
        print(json_response)


# Run the async code
asyncio.run(main())
