# Deep Research Agent

## Getting Started

### Prerequisites

Install [uv](https://docs.astral.sh/uv/) for modern, fast Python package management:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or with pip
pip install uv
```

### Setup

**Note:** This project uses `uv run` for all commands, which automatically manages the virtual environment without manual activation.

1. Install all dependencies (including dev dependencies and [LangGraph CLI](https://langchain-ai.github.io/langgraph/concepts/langgraph_cli/)):

```bash
cd path/to/your/app
uv sync --dev
```

This will:
- Create a virtual environment in `.venv/`
- Install the project in editable mode
- Install all dependencies including LangGraph CLI
- Generate a `uv.lock` file for reproducible builds

2. (Optional) Customize the code and project as needed. Create a `.env` file if you need to use secrets.

```bash
cp .env.example .env
```

If you want to enable LangSmith tracing, add your LangSmith API key to the `.env` file.

```text
# .env
LANGSMITH_API_KEY=lsv2...
```

3. Start the LangGraph Server.

```shell
# Use uv run (recommended - no activation needed)
uv run langgraph dev
```

For more information on getting started with LangGraph Server, [see here](https://langchain-ai.github.io/langgraph/tutorials/langgraph-platform/local-server/).

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/agent
```

### Development Tools

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy src/
```
