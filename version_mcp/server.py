"""MCP server for looking up package versions from various package managers."""

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

server = Server("version-mcp")


async def lookup_pypi(package_name: str) -> dict:
    """Look up a package on PyPI."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://pypi.org/pypi/{package_name}/json",
            follow_redirects=True,
        )
        if response.status_code == 404:
            return {"error": f"Package '{package_name}' not found on PyPI"}
        response.raise_for_status()
        data = response.json()

        info = data["info"]
        releases = list(data["releases"].keys())

        def get_upload_time(v: str) -> str:
            return data["releases"][v][0]["upload_time"] if data["releases"][v] else ""

        releases_sorted = sorted(releases, key=get_upload_time, reverse=True)

        return {
            "name": info["name"],
            "latest_version": info["version"],
            "summary": info.get("summary", ""),
            "recent_versions": releases_sorted[:10],
            "homepage": info.get("home_page") or info.get("project_url"),
            "requires_python": info.get("requires_python"),
        }


async def lookup_npm(package_name: str) -> dict:
    """Look up a package on npm."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://registry.npmjs.org/{package_name}",
            follow_redirects=True,
        )
        if response.status_code == 404:
            return {"error": f"Package '{package_name}' not found on npm"}
        response.raise_for_status()
        data = response.json()

        dist_tags = data.get("dist-tags", {})
        versions = list(data.get("versions", {}).keys())

        return {
            "name": data["name"],
            "latest_version": dist_tags.get("latest"),
            "description": data.get("description", ""),
            "dist_tags": dist_tags,
            "recent_versions": versions[-10:][::-1],
            "homepage": data.get("homepage"),
        }


async def lookup_crates(package_name: str) -> dict:
    """Look up a package on crates.io (Rust)."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://crates.io/api/v1/crates/{package_name}",
            headers={"User-Agent": "version-mcp/0.1.0"},
            follow_redirects=True,
        )
        if response.status_code == 404:
            return {"error": f"Package '{package_name}' not found on crates.io"}
        response.raise_for_status()
        data = response.json()

        crate = data["crate"]
        versions = [v["num"] for v in data.get("versions", [])]

        return {
            "name": crate["name"],
            "latest_version": crate.get("max_version"),
            "description": crate.get("description", ""),
            "recent_versions": versions[:10],
            "homepage": crate.get("homepage"),
            "repository": crate.get("repository"),
        }


async def lookup_go(module_path: str) -> dict:
    """Look up a Go module on pkg.go.dev."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://proxy.golang.org/{module_path}/@latest",
            follow_redirects=True,
        )
        if response.status_code == 404:
            return {"error": f"Module '{module_path}' not found on Go proxy"}
        response.raise_for_status()
        data = response.json()

        # Get version list
        versions_response = await client.get(
            f"https://proxy.golang.org/{module_path}/@v/list",
            follow_redirects=True,
        )
        versions = []
        if versions_response.status_code == 200:
            versions = versions_response.text.strip().split("\n")
            versions = [v for v in versions if v]

        return {
            "name": module_path,
            "latest_version": data.get("Version"),
            "recent_versions": versions[-10:][::-1] if versions else [data.get("Version")],
            "timestamp": data.get("Time"),
        }


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available version lookup tools."""
    return [
        Tool(
            name="lookup_pypi",
            description=(
                "Look up Python package versions on PyPI. "
                "Use this to find the latest version and recent releases of Python packages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The Python package name (e.g., 'requests', 'django')",
                    }
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="lookup_npm",
            description=(
                "Look up JavaScript/Node.js package versions on npm. "
                "Use this to find the latest version and recent releases of npm packages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The npm package name (e.g., 'react', 'express')",
                    }
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="lookup_crates",
            description=(
                "Look up Rust crate versions on crates.io. "
                "Use this to find the latest version and recent releases of Rust crates."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "description": "The Rust crate name (e.g., 'serde', 'tokio')",
                    }
                },
                "required": ["package_name"],
            },
        ),
        Tool(
            name="lookup_go",
            description=(
                "Look up Go module versions on the Go module proxy. "
                "Use this to find the latest version and recent releases of Go modules."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "module_path": {
                        "type": "string",
                        "description": "The Go module path (e.g., 'github.com/gin-gonic/gin')",
                    }
                },
                "required": ["module_path"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "lookup_pypi":
            result = await lookup_pypi(arguments["package_name"])
        elif name == "lookup_npm":
            result = await lookup_npm(arguments["package_name"])
        elif name == "lookup_crates":
            result = await lookup_crates(arguments["package_name"])
        elif name == "lookup_go":
            result = await lookup_go(arguments["module_path"])
        else:
            result = {"error": f"Unknown tool: {name}"}

        # Format result as readable text
        if "error" in result:
            text = result["error"]
        else:
            lines = [f"Package: {result['name']}"]
            lines.append(f"Latest Version: {result['latest_version']}")
            if result.get("description") or result.get("summary"):
                lines.append(f"Description: {result.get('description') or result.get('summary')}")
            if result.get("recent_versions"):
                lines.append(f"Recent Versions: {', '.join(result['recent_versions'])}")
            if result.get("dist_tags"):
                tags = [f"{k}={v}" for k, v in result["dist_tags"].items()]
                lines.append(f"Dist Tags: {', '.join(tags)}")
            if result.get("requires_python"):
                lines.append(f"Requires Python: {result['requires_python']}")
            if result.get("homepage"):
                lines.append(f"Homepage: {result['homepage']}")
            if result.get("repository"):
                lines.append(f"Repository: {result['repository']}")
            text = "\n".join(lines)

        return [TextContent(type="text", text=text)]
    except httpx.HTTPError as e:
        return [TextContent(type="text", text=f"HTTP error looking up package: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error looking up package: {e}")]


async def run():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point."""
    import asyncio

    asyncio.run(run())


if __name__ == "__main__":
    main()
