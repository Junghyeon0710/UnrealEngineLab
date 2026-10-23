"""Record live MCP discovery; never edits project assets or client configuration."""
import argparse
import datetime
import json
from pathlib import Path
from mcp_client import Client, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    dest = root / "Docs/UE/Evidence/UnrealMCP"
    dest.mkdir(parents=True, exist_ok=True)
    client = Client(args.endpoint)
    def write(name, data):
        (dest / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write("connection.json", {"captured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
          "endpoint": args.endpoint, "initialize": client.initialization,
          "tools_list": client.rpc("tools/list")})
    listing = client.tool("list_toolsets")
    write("toolsets.json", listing)
    names = [line[2:].split(":", 1)[0] for line in text(listing).splitlines()
             if line.startswith("- ") and "." in line[2:].split(":", 1)[0]
             and " " not in line[2:].split(":", 1)[0]]
    catalog = []
    for name in names:
        response = client.tool("describe_toolset", {"toolset_name": name})
        schema = json.loads(text(response))
        write(name + ".json", schema)
        catalog.append({"name": name, "description": schema.get("description", ""),
                        "tools": [tool["name"].rsplit(".", 1)[-1] for tool in schema.get("tools", [])]})
    write("catalog.json", catalog)
    print(json.dumps(catalog, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
