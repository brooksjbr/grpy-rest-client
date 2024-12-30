# Grpy REST Client

[![Tests](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml)
[![Lint](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml)

The Grpy REST Client is a modern Python library built on top of aiohttp that provides an elegant async-first approach to handling REST requests.

## Features

- Leverages aiohttp for high-performance asynchronous HTTP operations
- Implements async/await patterns for efficient concurrent requests
- Provides clean async context manager support through async with syntax
- Handles REST HTTP requests with full async capabilities

## Development Setup

1. Clone and enter the repository:

```bash
git clone https://github.com/brooksjbr/grpy-rest-client.git
cd grpy-rest-client
```

2. Create a virtual environment and activate it:

```bash
python3 tools/bootstrap_dev.py
source ~/projects/.venvs/grpy-rest-client/bin/activate
```

## Running Tests

```bash
pytest tests/
```
