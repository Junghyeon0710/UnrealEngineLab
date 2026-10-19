"""Small HTTP client for the Unreal MCP server (ModelContextProtocol plugin)."""
import base64
import ctypes
import json
import os
import urllib.request

ENDPOINT = os.environ.get("MVVM_MCP_ENDPOINT", "http://127.0.0.1:8000/mcp")
EDITOR = "EditorToolset.EditorAppToolset"
SLATE = "SlateInspectorToolset.SlateInspectorToolset"


class Client:
    def __init__(self, endpoint=ENDPOINT):
        self.endpoint = endpoint
        self.session = None
        self.next_id = 0
        self.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "mvvm-lab", "version": "1.0"}})

    def rpc(self, method, params):
        self.next_id += 1
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        body = json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}).encode()
        with urllib.request.urlopen(urllib.request.Request(self.endpoint, body, headers), timeout=300) as response:
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
    """Decode a ToolsetRegistry return value without printing image payloads."""
    if result.get("isError"):
        raise RuntimeError(result)
    data = json.loads(next(c["text"] for c in result["content"] if c["type"] == "text"))
    return data.get("returnValue", data)


def save_image(result, path):
    """Write an FToolsetImage return value (editor or Slate capture) to a PNG file."""
    image = value(result)
    path.write_bytes(base64.b64decode(image["data"]))
    return path


def lab(c, action, options=None):
    """Call a named action of the MVVMLabToolset registered by register_toolset.py."""
    if not hasattr(c, "lab_toolset"):
        listing = c.tool("list_toolsets")["content"][0]["text"]
        # The registered name depends on where the script lives (PythonTypes.* or Game.Scripts.*).
        c.lab_toolset = next(line[2:].split(":", 1)[0] for line in listing.splitlines()
                             if line.startswith("- ") and "MVVMLabToolset" in line.split(":", 1)[0])
    result = c.call(c.lab_toolset, "run_action", {"action": action, "options_json": json.dumps(options or {})})
    return json.loads(value(result))


def restore_editor_window(title_prefix):
    """A minimized editor ticks PIE at a few frames per second, so bring it back before recording."""
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def visit(hwnd, _):
        buffer = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buffer, 256)
        if buffer.value.startswith(title_prefix) and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(visit, 0)
    for hwnd in found:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    return bool(found)
