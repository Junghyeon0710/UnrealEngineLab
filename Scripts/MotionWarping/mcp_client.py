"""Local Unreal MCP client used for the reproducible editor investigation."""
from pathlib import Path
import json
import sys
import urllib.request

ENDPOINT = "http://127.0.0.1:8000/mcp"


class Client:
    def __init__(self, endpoint=ENDPOINT):
        self.endpoint = endpoint
        self.session = None
        self.next_id = 0
        self.rpc("initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "codex-motionwarping-lab", "version": "1.0"}
        })

    def rpc(self, method, params):
        self.next_id += 1
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        body = json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}).encode()
        with urllib.request.urlopen(urllib.request.Request(self.endpoint, body, headers), timeout=180) as response:
            self.session = response.headers.get("Mcp-Session-Id", self.session)
            result = json.loads(response.read())
        if "error" in result:
            raise RuntimeError(result["error"])
        return result.get("result", {})

    def tool(self, name, arguments=None):
        return self.rpc("tools/call", {"name": name, "arguments": arguments or {}})

    def call(self, toolset, tool, arguments=None):
        return self.tool("call_tool", {"toolset_name": toolset, "tool_name": tool, "arguments": arguments or {}})


def value(result):
    """Decode a ToolsetRegistry text return without printing image payloads."""
    if result.get("isError"):
        raise RuntimeError(result)
    data = json.loads(next(c["text"] for c in result["content"] if c["type"] == "text"))
    return data.get("returnValue", data)


def sample_client():
    return Client("http://127.0.0.1:8001/mcp")


def lab(c, action, options=None):
    if not hasattr(c, "lab_toolset"):
        text = c.tool("list_toolsets")["content"][0]["text"]
        c.lab_toolset = next(line[2:].split(":", 1)[0] for line in text.splitlines() if line.startswith("- PythonTypes.MotionWarpingLabToolset"))
    name = c.lab_toolset
    return json.loads(value(c.call(name, "run_action", {"action": action, "options_json": json.dumps(options or {})})))


if __name__ == "__main__":
    client = Client()
    arguments = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")) if len(sys.argv) > 2 else {}
    result = client.tool(sys.argv[1], arguments)
    print(json.dumps(result, ensure_ascii=False, indent=2))
