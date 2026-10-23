"""Create, inspect and remove one demo cube in the current editor world; no saves."""
import json
from pathlib import Path
from mcp_client import Client, value, save_image

ROOT = Path(__file__).resolve().parents[2]
SCENE = "editor_toolset.toolsets.scene.SceneTools"
ACTOR = "editor_toolset.toolsets.actor.ActorTools"
EDITOR = "EditorToolset.EditorAppToolset"


def main():
    client = Client()
    captures = ROOT / "Saved/UnrealMCPDocs/demo"
    captures.mkdir(parents=True, exist_ok=True)
    evidence = []
    def call(toolset, tool, args=None):
        result = value(client.call(toolset, tool, args))
        evidence.append({"toolset": toolset, "tool": tool, "arguments": args or {}, "result": result})
        return result
    old_camera = call(EDITOR, "GetCameraTransform")
    actor = None
    try:
        call(EDITOR, "SetCameraTransform", {"transform": {"location": {"x": -450, "y": -650, "z": 350},
             "rotation": {"pitch": -18, "yaw": 55, "roll": 0}}})
        actor = call(SCENE, "add_to_scene_from_asset", {"asset_path": "/Engine/BasicShapes/Cube.Cube",
             "name": "MCP_DemoCube", "xform": {"location": {"x": 0, "y": 0, "z": 100}}})
        call(EDITOR, "SelectActors", {"actors": [actor]})
        for i, (x, z, yaw) in enumerate([(0,100,0), (0,100,0), (100,100,0), (200,100,0), (200,180,0), (200,180,45), (200,180,90)]):
            call(ACTOR, "set_actor_transform", {"actor": actor, "xform": {"location": {"x": x, "y": 0, "z": z},
                  "rotation": {"pitch": 0, "yaw": yaw, "roll": 0}}})
            call(ACTOR, "get_actor_transform", {"actor": actor})
            save_image(client.call(EDITOR, "CaptureViewport", {"captureTransform": None, "annotations": None, "bShowUI": True}), captures / f"{i:02}.png")
        save_image(client.call(EDITOR, "CaptureEditorImage"), ROOT / "Docs/UE/Images/unreal-mcp-demo-editor.png")
    finally:
        if actor:
            call(SCENE, "remove_from_scene", {"actor": actor})
        call(EDITOR, "SetCameraTransform", {"transform": old_camera})
        (ROOT / "Docs/UE/Evidence/UnrealMCP/demo.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
