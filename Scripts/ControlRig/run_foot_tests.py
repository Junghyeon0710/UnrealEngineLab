"""Foot placement Control Rig trials on GameAnimationSample's curved ramp, through Unreal MCP.

The editor must run the MCP server and have register_toolset.py executed once (see README.md).
The Mover pawn (DDCvar.PawnClass 1) uses CR_Biped_FootPlacement; a.AnimNode.FootPlacement.Enable
switches its AnimBP between that rig and plain Leg IK. Sample assets are never saved.
"""
from pathlib import Path
from datetime import datetime
import argparse
import json
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/ControlRigLab"
RAMP_Y = 1600.0                                   # middle of the ramp (it spans y 1400..1800)
SLOPES = {0: 1200.0, 10: 2600.0, 20: 3350.0, 30: 4100.0, 40: 4700.0}   # slope in degrees -> x on the ramp
FRONT = {"dx": 0.0, "dy": 600.0, "dz": 10.0, "look_dx": 0.0, "look_dy": 0.0, "look_dz": -30.0, "fov": 40.0}
DEBUG = {"ControlRig.EnableDrawInterfaceInGame": 1, "a.AnimNode.ControlRig.Debug": 1, "a.AnimNode.FootPlacement.Debug": 1}
NO_DEBUG = {name: 0 for name in DEBUG}
WALK = {"x": 4100.0, "y": 1430.0, "segments": [[0.3, 2.3, 90.0, 0.4]], "duration": 2.8}   # across the 30 degree part


def wait_recording(client):
    deadline = time.monotonic() + 180
    while True:
        status = lab(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            lab(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(0.4)


def archive(name):
    folder = EVIDENCE / name
    if folder.exists():
        target = EVIDENCE / "archive" / (name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        target.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(target)


def place(client, x, y, yaw, camera):
    """GASP's CustomTeleport onto the ramp, then wait until the pawn stands on it."""
    ground = lab(client, "ground_profile", {"points": [[x, y]]})["points"][0]["z"]
    lab(client, "prepare_character", {"location": [x, y, ground + 130.0], "yaw": yaw, "camera": camera})
    time.sleep(2.5)
    feet = lab(client, "sample_feet", {})
    assert feet["actor"][2] - ground < 100.0, ("pawn did not land", feet["actor"], ground)
    return ground


def record(client, name, seconds=1.0, capture_once=True, **extra):
    archive(name)
    options = {"case": name, "segments": [], "duration": seconds, "capture": capture_once, "interval": 100.0,
               "capture_time_dilation": 1.0}
    options.update(extra)
    lab(client, "start_run", options)
    return wait_recording(client)


def standing(client):
    for degrees, x in SLOPES.items():
        place(client, x, RAMP_Y, 90.0, FRONT)          # face +Y: left foot uphill (+X), right foot downhill
        for state in (1, 0):
            lab(client, "console", {"cvars": {"a.AnimNode.FootPlacement.Enable": state}})
            time.sleep(1.2)                            # the AnimBP blends rig <-> Leg IK over 0.2s
            print(f"slope_{degrees}_{'on' if state else 'off'}", record(client, f"slope_{degrees}_{'on' if state else 'off'}",
                  setup={"slope": degrees, "foot_placement": state}), flush=True)
        lab(client, "console", {"cvars": {"a.AnimNode.FootPlacement.Enable": 1}})


def debug_still(client):
    place(client, SLOPES[30], RAMP_Y, 90.0, FRONT)
    lab(client, "console", {"cvars": dict(DEBUG, **{"a.AnimNode.FootPlacement.Enable": 1})})
    time.sleep(1.0)
    print("debug_30", record(client, "debug_30", setup={"slope": 30, "debug": DEBUG}), flush=True)
    lab(client, "console", {"cvars": NO_DEBUG})


def walking(client):
    for state in (1, 0):
        lab(client, "console", {"cvars": {"a.AnimNode.FootPlacement.Enable": state}})
        place(client, WALK["x"], WALK["y"], 90.0, FRONT)
        name = f"walk_30_{'on' if state else 'off'}"
        archive(name)
        lab(client, "start_run", {"case": name, "segments": WALK["segments"], "duration": WALK["duration"], "capture": True,
                                  "interval": 1 / 30, "capture_time_dilation": 0.2,
                                  "setup": {"slope": 30, "foot_placement": state, "walk": WALK}})
        print(name, wait_recording(client), flush=True)
    lab(client, "console", {"cvars": {"a.AnimNode.FootPlacement.Enable": 1}})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part", action="append", choices=["standing", "debug", "walking"])
    args = parser.parse_args()
    client = Client()
    lab(client, "close_asset_previews", {"assets": value(client.call(EDITOR, "GetOpenAssets"))})
    restore_editor_window("GameAnimationSample")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    lab(client, "console", {"editor": True, "cvars": {"DDCvar.PawnClass": 1}})    # GM_Sandbox spawns the Mover pawn
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 1.0}}))
    time.sleep(1.5)
    lab(client, "configure_view")
    audit = lab(client, "capture_audit")
    assert "SandboxCharacter_Mover" in audit["pawn"], audit
    parts = args.part or ["standing", "debug", "walking"]
    if "standing" in parts:
        standing(client)
    if "debug" in parts:
        debug_still(client)
    if "walking" in parts:
        walking(client)
    value(client.call(EDITOR, "StopPIE"))
    rig = lab(client, "inspect_rig", {"path": "/Game/Blueprints/ControlRigs/CR_Biped_FootPlacement"})
    compact = {"path": rig["path"], "variables": rig["variables"],
               "hierarchy": [h for h in rig["hierarchy"] if not h["type"].startswith("BONE")],
               "bone_count": sum(1 for h in rig["hierarchy"] if h["type"].startswith("BONE")),
               "graphs": [{"name": g["name"], "nodes": len(g["nodes"]), "comments": [c["text"] for c in g["comments"]]}
                          for g in rig["graphs"]]}
    (EVIDENCE / "rig_structure.json").write_text(json.dumps(compact, indent=1), encoding="utf-8")
    lab(client, "restore_session", {"reset": ["DDCvar.PawnClass 0", "a.AnimNode.FootPlacement.Enable 1",
                                              "ControlRig.EnableDrawInterfaceInGame 0", "a.AnimNode.ControlRig.Debug 0",
                                              "a.AnimNode.FootPlacement.Debug 0"]})
    print("Trials completed.", flush=True)
