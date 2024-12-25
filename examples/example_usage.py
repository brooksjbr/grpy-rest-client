import asyncio

from grpy.rest_client import RestClient


async def main():
    async with RestClient(
        "https://jsonplaceholder.typicode.com", endpoint="users"
    ) as client:
        response = await client.handle_request(params={"page": 1})
        return response


# Run the async code
response = asyncio.run(main())
print(response)
