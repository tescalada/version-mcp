import pytest
import respx
from httpx import Response

from version_mcp.server import (
    call_tool,
    list_tools,
    lookup_crates,
    lookup_go,
    lookup_npm,
    lookup_pypi,
)


@pytest.fixture
def pypi_response():
    return {
        "info": {
            "name": "flask",
            "version": "3.0.0",
            "summary": "A simple framework for building complex web applications.",
            "home_page": "https://palletsprojects.com/p/flask",
            "requires_python": ">=3.8",
        },
        "releases": {
            "3.0.0": [{"upload_time": "2023-09-30T00:00:00"}],
            "2.3.3": [{"upload_time": "2023-08-21T00:00:00"}],
            "2.3.2": [{"upload_time": "2023-05-01T00:00:00"}],
        },
    }


@pytest.fixture
def npm_response():
    return {
        "name": "express",
        "description": "Fast, unopinionated, minimalist web framework",
        "dist-tags": {"latest": "4.18.2", "next": "5.0.0-beta.1"},
        "versions": {
            "4.18.0": {},
            "4.18.1": {},
            "4.18.2": {},
        },
        "homepage": "http://expressjs.com/",
    }


@pytest.fixture
def crates_response():
    return {
        "crate": {
            "name": "serde",
            "max_version": "1.0.193",
            "description": "A generic serialization/deserialization framework",
            "homepage": "https://serde.rs",
            "repository": "https://github.com/serde-rs/serde",
        },
        "versions": [
            {"num": "1.0.193"},
            {"num": "1.0.192"},
            {"num": "1.0.191"},
        ],
    }


@pytest.fixture
def go_latest_response():
    return {
        "Version": "v1.9.1",
        "Time": "2023-06-01T00:00:00Z",
    }


class TestLookupPypi:
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_lookup(self, pypi_response):
        respx.get("https://pypi.org/pypi/flask/json").mock(return_value=Response(200, json=pypi_response))

        result = await lookup_pypi("flask")

        assert result["name"] == "flask"
        assert result["latest_version"] == "3.0.0"
        assert result["summary"] == "A simple framework for building complex web applications."
        assert "3.0.0" in result["recent_versions"]

    @respx.mock
    @pytest.mark.asyncio
    async def test_package_not_found(self):
        respx.get("https://pypi.org/pypi/nonexistent-package-xyz/json").mock(return_value=Response(404))

        result = await lookup_pypi("nonexistent-package-xyz")

        assert "error" in result
        assert "not found" in result["error"]


class TestLookupNpm:
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_lookup(self, npm_response):
        respx.get("https://registry.npmjs.org/express").mock(return_value=Response(200, json=npm_response))

        result = await lookup_npm("express")

        assert result["name"] == "express"
        assert result["latest_version"] == "4.18.2"
        assert result["dist_tags"]["next"] == "5.0.0-beta.1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_package_not_found(self):
        respx.get("https://registry.npmjs.org/nonexistent-package-xyz").mock(return_value=Response(404))

        result = await lookup_npm("nonexistent-package-xyz")

        assert "error" in result
        assert "not found" in result["error"]


class TestLookupCrates:
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_lookup(self, crates_response):
        respx.get("https://crates.io/api/v1/crates/serde").mock(return_value=Response(200, json=crates_response))

        result = await lookup_crates("serde")

        assert result["name"] == "serde"
        assert result["latest_version"] == "1.0.193"
        assert result["repository"] == "https://github.com/serde-rs/serde"

    @respx.mock
    @pytest.mark.asyncio
    async def test_package_not_found(self):
        respx.get("https://crates.io/api/v1/crates/nonexistent-crate-xyz").mock(return_value=Response(404))

        result = await lookup_crates("nonexistent-crate-xyz")

        assert "error" in result
        assert "not found" in result["error"]


class TestLookupGo:
    @respx.mock
    @pytest.mark.asyncio
    async def test_successful_lookup(self, go_latest_response):
        respx.get("https://proxy.golang.org/github.com/gin-gonic/gin/@latest").mock(
            return_value=Response(200, json=go_latest_response)
        )
        respx.get("https://proxy.golang.org/github.com/gin-gonic/gin/@v/list").mock(
            return_value=Response(200, text="v1.9.0\nv1.9.1\n")
        )

        result = await lookup_go("github.com/gin-gonic/gin")

        assert result["name"] == "github.com/gin-gonic/gin"
        assert result["latest_version"] == "v1.9.1"

    @respx.mock
    @pytest.mark.asyncio
    async def test_module_not_found(self):
        respx.get("https://proxy.golang.org/github.com/nonexistent/module/@latest").mock(return_value=Response(404))

        result = await lookup_go("github.com/nonexistent/module")

        assert "error" in result
        assert "not found" in result["error"]


class TestCallTool:
    @respx.mock
    @pytest.mark.asyncio
    async def test_call_pypi_tool(self, pypi_response):
        respx.get("https://pypi.org/pypi/flask/json").mock(return_value=Response(200, json=pypi_response))

        result = await call_tool("lookup_pypi", {"package_name": "flask"})

        assert len(result) == 1
        assert "flask" in result[0].text
        assert "3.0.0" in result[0].text

    @respx.mock
    @pytest.mark.asyncio
    async def test_call_unknown_tool(self):
        result = await call_tool("unknown_tool", {})

        assert "Unknown tool" in result[0].text


class TestListTools:
    @pytest.mark.asyncio
    async def test_lists_all_tools(self):
        tools = await list_tools()

        tool_names = [t.name for t in tools]
        assert "lookup_pypi" in tool_names
        assert "lookup_npm" in tool_names
        assert "lookup_crates" in tool_names
        assert "lookup_go" in tool_names
