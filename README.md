# GrPy REST Client

[![Tests](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/test.yml)
[![Lint](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml/badge.svg)](https://github.com/brooksjbr/grpy-rest-client/actions/workflows/lint.yml)

Generic extraction module, fetches data from APIs

## Features

-   Makes Restful requests URLs

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
