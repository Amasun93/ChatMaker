"""Host-neutral ChatMaker stdio MCP entry point.

The wire protocol and all 24 tools remain in the established server while host
installers refer to this stable, generic module name.
"""

from .workbuddy_mcp import *  # noqa: F403
from .workbuddy_mcp import main


if __name__ == "__main__":
    raise SystemExit(main())
