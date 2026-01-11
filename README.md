# version-mcp

MCP server for looking up package versions from various package managers.

## Tools

- **lookup_pypi** - Python packages from PyPI
- **lookup_npm** - JavaScript packages from npm
- **lookup_crates** - Rust crates from crates.io
- **lookup_go** - Go modules from the Go module proxy

## Usage with Claude Code

```bash
claude mcp add version-mcp -- uvx version-mcp
```

## Development

Run tests:

```bash
uv run --extra dev pytest -v
```

Lint/format:

```bash
uv run --extra dev ruff check .
uv run --extra dev ruff format .
```
