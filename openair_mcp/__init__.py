"""openair-3-mcp — MCP server wrapping the R openair package."""
from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("openair-3-mcp")
except PackageNotFoundError:
    __version__ = "0.1.0"
