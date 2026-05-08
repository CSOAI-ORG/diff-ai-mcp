<div align="center">

# Diff Ai MCP

**MCP server for diff ai mcp operations**

[![PyPI](https://img.shields.io/pypi/v/meok-diff-ai-mcp)](https://pypi.org/project/meok-diff-ai-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![MEOK AI Labs](https://img.shields.io/badge/MEOK_AI_Labs-MCP_Server-purple)](https://meok.ai)

</div>

## Overview

Diff Ai MCP provides AI-powered tools via the Model Context Protocol (MCP).

## Tools

| Tool | Description |
|------|-------------|
| `diff_texts` | Generate a unified diff between two text inputs. |
| `diff_files` | Generate a diff between two file contents in unified, context, or ndiff format. |
| `generate_patch` | Generate a patch file from original and modified text that can be applied with t |
| `apply_patch` | Apply a unified diff patch to the original text and return the result. |

## Installation

```bash
pip install meok-diff-ai-mcp
```

## Usage with Claude Desktop

Add to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "diff-ai": {
      "command": "python",
      "args": ["-m", "meok_diff_ai_mcp.server"]
    }
  }
}
```

## Usage with FastMCP

```python
from mcp.server.fastmcp import FastMCP

# This server exposes 4 tool(s) via MCP
# See server.py for full implementation
```

## License

MIT © [MEOK AI Labs](https://meok.ai)
