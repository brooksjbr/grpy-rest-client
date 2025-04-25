[![Tests](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml)
[![Lint](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml)

# GRPY REST Client

A Python package for making HTTP requests with support for asynchronous operations, pagination strategies, and retry mechanisms.

## Features

-   **Asynchronous HTTP Client**: Built on aiohttp for efficient asynchronous requests
-   **Pagination Support**: Multiple pagination strategies including:
    -   Page number pagination
    -   HATEOAS link-based pagination
-   **Retry Mechanisms**: Configurable retry strategies with exponential backoff
-   **Error Handling**: Comprehensive error handling and status code management
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

Here's a basic example of using the REST client:

```python
from grpy_rest_client import RestClient

async def main():
    # Create a client with a base URL
    async with RestClient(base_url="https://api.example.com") as client:
        # Make a GET request
        response = await client.get("/resource")
        data = await response.json()
        print(data)

        # Make a POST request with data
        response = await client.post(
            "/resource",
            json={"name": "example"}
        )
        result = await response.json()
        print(result)
```

### Pagination Example

```python
from grpy_rest_client import RestClient
from grpy_rest_client.pagination import PageNumberPaginationStrategy

async def main():
    # Create a pagination strategy
    pagination = PageNumberPaginationStrategy()

    # Create a client
    async with RestClient(base_url="https://api.example.com") as client:
        # Get all pages of data
        all_items = []
        async for items in client.paginate("/resources", pagination_strategy=pagination):
            all_items.extend(items)

        print(f"Retrieved {len(all_items)} items")
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
