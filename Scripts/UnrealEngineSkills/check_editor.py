"""Read-only checks of the running editor: what the plugin's skills rely on, plus answers for the A/B prompts.

    python Scripts/UnrealEngineSkills/check_editor.py --endpoint http://127.0.0.1:8000/mcp
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Scripts/UnrealMCP"))
from mcp_client import Client, text  # noqa: E402

SCENE = "editor_toolset.toolsets.scene.SceneTools"
BP = "editor_toolset.toolsets.blueprint.BlueprintTools"
BP_PATH = "/Game/Blueprints/MovementModes/BP_MovementMode_Slide.BP_MovementMode_Slide"


def value(result):
    data = json.loads(text(result))
    return data.get("returnValue", data) if isinstance(data, dict) else data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/mcp")
    args = parser.parse_args()
    c = Client(args.endpoint)
    out = {"protocol": c.initialization.get("protocolVersion")}

    tools = c.rpc("tools/list")["tools"]
    out["tools_list"] = [t["name"] for t in tools]
    out["tools_list_bytes"] = len(json.dumps(tools, separators=(",", ":"), ensure_ascii=False))

    listing = text(c.tool("list_toolsets"))
    out["list_toolsets_bytes"] = len(listing.encode("utf-8"))
    names = []
    for line in listing.splitlines():
        head = line[2:].split(":", 1)[0] if line.startswith("- ") else ""
        if "." in head and " " not in head:
            names.append(head)
    out["toolset_count"] = len(names)
    out["toolsets"] = names
    for key in ("AgentSkill", "LiveCoding", "Programmatic", "AIAssistant"):
        out[f"has_{key}"] = [n for n in names if key.lower() in n.lower()]

    tool_count = schema_bytes = 0
    for name in names:
        entries = json.loads(text(c.tool("describe_toolset", {"toolset_name": name}))).get("tools", [])
        tool_count += len(entries)
        schema_bytes += sum(len(json.dumps(t, separators=(",", ":"), ensure_ascii=False)) for t in entries)
    out["tool_count"] = tool_count
    out["all_schema_bytes"] = schema_bytes
    out["agent_skills"] = value(c.call("ToolsetRegistry.AgentSkillToolset", "ListSkills"))

    truth = {"level": value(c.call(SCENE, "get_current_level"))}
    actors = value(c.call(SCENE, "find_actors", {"name": "", "tag": "", "collision_channels": []}))
    truth["actors"] = [a["refPath"].rsplit(".", 1)[-1] for a in actors]
    bp = {"refPath": BP_PATH}
    for tool in ("get_parent", "list_variables", "list_functions"):
        truth[tool] = value(c.call(BP, tool, {"blueprint": bp}))

    dest = ROOT / "Docs/UE/Evidence/UnrealEngineSkills"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "editor_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (dest / "ground_truth.json").write_text(json.dumps(truth, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{out['toolset_count']} toolsets, {tool_count} tools, {schema_bytes} schema bytes, "
          f"{len(out['agent_skills'])} agent skills, {len(truth['actors'])} actors")


if __name__ == "__main__":
    main()
