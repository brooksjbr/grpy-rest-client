# Grpy REST Client

[![Tests](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml)
[![Lint](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml)

A simple rest client to manage http requests.

## Features

-   Makes RESTful HTTP requests

## Development Setup

1. Clone and enter the repository:

```bash
git clone https://github.com/brooksjbr/grpy-rest-client.git
cd grpy-rest-client
```

2. Create a virtual environment and activate it:

```bash
python3 tools/bootstrap.py
source ~/projects/.venv/grpy-rest-client/bin/activate
```

## Running Tests

```bash
pytest tests/
```
