"""Local HTTP client used by the Unreal MCP documentation examples (UE 5.8.3)."""
import base64
import json
import urllib.request
from pathlib import Path


class Client:
    def __init__(self, endpoint="http://127.0.0.1:8000/mcp", timeout=30):
        self.endpoint, self.timeout = endpoint, timeout
        self.session, self.next_id = None, 0
        self.initialization = self.rpc("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "unreal-mcp-docs", "version": "1.0"},
        })
        self.rpc("notifications/initialized", {}, notification=True)

    def rpc(self, method, params=None, notification=False):
        body = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        if not notification:
            self.next_id += 1
            body["id"] = self.next_id
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.endpoint, json.dumps(body).encode(), headers)
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            self.session = response.headers.get("Mcp-Session-Id", self.session)
            raw = response.read().decode()
        if not raw:
            return None
        # This local build returns JSON; also accept a single SSE result event.
        if raw.lstrip().startswith("event:") or raw.lstrip().startswith("data:"):
            raw = "\n".join(line[5:].lstrip() for line in raw.splitlines() if line.startswith("data:"))
        data = json.loads(raw)
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

    def tool(self, name, arguments=None):
        result = self.rpc("tools/call", {"name": name, "arguments": arguments or {}})
        if result.get("isError"):
            raise RuntimeError(result)
        return result

    def call(self, toolset, tool, arguments=None):
        return self.tool("call_tool", {"toolset_name": toolset, "tool_name": tool, "arguments": arguments or {}})


def text(result):
    return "\n".join(block["text"] for block in result.get("content", []) if block["type"] == "text")


def value(result):
    data = json.loads(text(result))
    return data.get("returnValue", data) if isinstance(data, dict) else data


def save_image(result, path):
    data = value(result)
    data = data.get("image", data)
    Path(path).write_bytes(base64.b64decode(data["data"]))
