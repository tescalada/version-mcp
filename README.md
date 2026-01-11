# version-mcp

MCP server for looking up package versions from various package managers.

## Tools

- **lookup_pypi** - Python packages from PyPI
- **lookup_npm** - JavaScript packages from npm
- **lookup_crates** - Rust crates from crates.io
- **lookup_go** - Go modules from the Go module proxy

## Usage with Claude Code

From git:

```bash
claude mcp add version-mcp -- uvx --from git+https://github.com/tescalada/version-mcp version-mcp
```

From local checkout:

```bash
claude mcp add version-mcp -- uv run --directory /path/to/version_mcp version-mcp
```

## Development

Run tests:

```bash
uv run --extra dev pytest -v
```
