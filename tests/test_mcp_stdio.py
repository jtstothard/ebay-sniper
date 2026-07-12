#!/usr/bin/env python3
"""Simple MCP stdio test - validates tool discovery"""

import asyncio
import json
import sys


async def test_mcp_stdio():
    """Test MCP server via stdio"""
    import subprocess

    # Start the MCP server
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        "from sniper.mcp_server import main; import asyncio; asyncio.run(main())",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Send initialize request
    initialize = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }

    proc.stdin.write((json.dumps(initialize) + "\n").encode())
    await proc.stdin.drain()

    # Read response
    line = await proc.stdout.readline()
    if not line:
        print("ERROR: No response from server")
        return False

    response = json.loads(line.decode().strip())
    print(f"Initialize response: {json.dumps(response, indent=2)}")

    if "error" in response:
        print(f"ERROR: Initialize failed: {response['error']}")
        return False

    # Send initialized notification
    initialized = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    proc.stdin.write((json.dumps(initialized) + "\n").encode())
    await proc.stdin.drain()

    # List tools
    list_tools = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    proc.stdin.write((json.dumps(list_tools) + "\n").encode())
    await proc.stdin.drain()

    # Read tools response
    line = await proc.stdout.readline()
    if not line:
        print("ERROR: No response to tools/list")
        return False

    response = json.loads(line.decode().strip())
    print(f"\nTools response: {json.dumps(response, indent=2)}")

    if "error" in response:
        print(f"ERROR: tools/list failed: {response['error']}")
        return False

    tools = response.get("result", {}).get("tools", [])
    print(f"\n✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")

    # Verify expected tools
    expected = {"add_watch", "list_watches", "cancel_watch", "search_auctions"}
    found = {t["name"] for t in tools}
    missing = expected - found

    if missing:
        print(f"\n✗ Missing tools: {missing}")
        return False
    else:
        print(f"\n✓ All expected tools present!")

    # Clean up
    proc.stdin.close()
    await proc.wait()

    return True


if __name__ == "__main__":
    import os

    os.chdir("/home/hermes/work/ebay-sniper")
    success = asyncio.run(test_mcp_stdio())
    sys.exit(0 if success else 1)