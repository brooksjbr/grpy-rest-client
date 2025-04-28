[![Tests](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml)
[![Lint](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml)

# GRPY REST Client

A Python package for making HTTP requests with support for asynchronous operations, pagination strategies, and retry mechanisms.

## Features

-   **Async-First Design**: Built on aiohttp for efficient asynchronous requests, optimized for high-throughput microservices
-   **Comprehensive Pagination Support**:
    -   Protocol-based design with multiple strategy implementations
    -   Page number pagination
    -   HATEOAS link-based pagination
    -   Configurable data extraction from nested responses
-   **Advanced Retry Mechanisms**:
    -   Policy registry with multiple retry strategies
    -   Exponential backoff with configurable parameters
    -   Fixed delay option
    -   Intelligent retry decisions based on HTTP status codes
-   **Robust Error Handling**:
    -   Comprehensive exception handling with detailed logging
    -   Status code management
    -   Context-aware error reporting
-   **Resource Management**:
    -   Proper session lifecycle management with AsyncExitStack
    -   Automatic cleanup of resources
-   **Structured Logging**:

    -   Configurable log levels and formats
    -   Console and file output options
    -   Contextual information for debugging

-   **Type Safety**: Built with Pydantic for robust data validation

## Installation

### From Source

Clone the repository and install the package:

```bash
git clone https://github.com/brooksjbr/grpy-rest-client.git
cd grpy-rest-client
pip install -e .
```

### Development Environment Setup

This project includes a bootstrap script to set up a virtual environment:

```bash
# Set the path where you want to create the virtual environment
export PYTHON_VENV_PATH=~/venvs
# Run the bootstrap script
python scripts/bootstrap_venv.py
```

After running the script, activate the virtual environment:

```bash
source ~/venvs/grpy-rest-client/bin/activate
```

## Usage

### Basic REST Client Usage

```python
from grpy.rest_client import RestClient
from grpy.logging import Logger

async def main():
    # Create a client with a base URL and custom logger
    logger = Logger(name="my-app", level=Logger.DEBUG)

    async with RestClient(
        base_url="https://api.example.com",
        logger=logger
    ) as client:
        # Make a GET request
        response = await client.get("/resource")
        data = await response.json()
        print(data)

        # Make a POST request with data
        response = await client.post(
            "/resource",
            json={"name": "example"},
            timeout=30  # Custom timeout in seconds
        )
        result = await response.json()
        print(result)
```

### Pagination Example

```python
from grpy.rest_client import RestClient
from grpy.pagination_strategies import PageNumberPaginationStrategy, HateoasPaginationStrategy

async def main():
    # Create a client
    async with RestClient(base_url="https://api.example.com") as client:
        # Page number pagination example
        page_strategy = PageNumberPaginationStrategy(
            page_param="page",
            size_param="size",
            page_size=25
        )

        # Get all pages of data with page number pagination
        all_items = []
        async for items in client.paginate(
            "/resources",
            pagination_strategy=page_strategy,
            params={"category": "books"}
        ):
            all_items.extend(items)

        print(f"Retrieved {len(all_items)} items using page number pagination")

        # HATEOAS pagination example
        hateoas_strategy = HateoasPaginationStrategy()

        # Get all pages of data with HATEOAS pagination
        all_events = []
        async for events in client.paginate(
            "/events",
            pagination_strategy=hateoas_strategy,
            data_key="_embedded.events"  # Extract data from nested structure
        ):
            all_events.extend(events)

        print(f"Retrieved {len(all_events)} events using HATEOAS pagination")
```

### Retry Example

```python
from grpy.rest_client import RestClient
from grpy.retry_policies import ExponentialBackoffRetryPolicy

async def main():
    # Create a retry policy
    retry_policy = ExponentialBackoffRetryPolicy(
        max_retries=5,
        initial_delay=0.1,
        max_delay=10.0,
        backoff_factor=2.0,
        jitter=True
    )

    # Create a client with the retry policy
    async with RestClient(
        base_url="https://api.example.com",
        retry_policy=retry_policy,
        retryable_status_codes=[429, 500, 502, 503, 504]  # Status codes to retry
    ) as client:
        # Requests will automatically use the retry policy
        try:
            response = await client.get("/flaky-endpoint")
            data = await response.json()
            print(data)
        except Exception as e:
            print(f"Failed after multiple retries: {e}")

        # Combine pagination and retry
        async for items in client.paginate(
            "/large-collection",
            pagination_strategy=PageNumberPaginationStrategy(),
            # Pagination will also use the configured retry policy
        ):
            process_items(items)
```

### Advanced Configuration

```python
from grpy.rest_client import RestClient
from grpy.logging import Logger
from grpy.retry_manager import RetryManager
from grpy.retry_policies import FixedDelayRetryPolicy

async def main():
    # Custom retry manager with multiple policies
    retry_manager = RetryManager()
    retry_manager.register_policy("fixed", FixedDelayRetryPolicy(
        max_retries=3,
        delay=1.0
    ))
    retry_manager.set_default_policy("fixed")

    # Create a client with custom headers and advanced configuration
    async with RestClient(
        base_url="https://api.example.com",
        headers={
            "Authorization": "Bearer token123",
            "X-API-Key": "your-api-key"
        },
        timeout=60,
        retry_manager=retry_manager,
        logger=Logger(name="api-client", level=Logger.INFO, log_file="api.log")
    ) as client:
        # The client will use all the configured components
        response = await client.get("/secure-resource")
        print(await response.json())
```

## Development

### Running Tests

To run the test suite:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/grpy_rest_client
```

### Code Style

This project uses:

-   Black for code formatting
-   Flake8 for linting
-   isort for import sorting

To check code style:

```bash
# Check formatting
black --check src tests

# Check linting
flake8 src tests

# Check import sorting
isort --check-only src tests
```

To automatically format code:

```bash
black src tests
isort src tests
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/) for commit messages. This enables automatic versioning and changelog generation.

Basic format:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

Types include:

-   `feat`: A new feature
-   `fix`: A bug fix
-   `docs`: Documentation changes
-   `style`: Code style changes (formatting, etc.)
-   `refactor`: Code changes that neither fix bugs nor add features
-   `perf`: Performance improvements
-   `test`: Adding or correcting tests
-   `build`: Changes to build system or dependencies
-   `ci`: Changes to CI configuration
-   `chore`: Other changes that don't modify src or test files

For breaking changes, add an exclamation mark before the colon and include a "BREAKING CHANGE:" section in the footer.

## Versioning

This project uses [Semantic Versioning](https://semver.org/) and automatically generates version numbers based on commit messages using python-semantic-release.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
