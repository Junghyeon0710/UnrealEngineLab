"""LookAtPOI (CR_AdjustToPOI) trials in GameAnimationSample's LookAtPOI_Level, through Unreal MCP.

The PIE player character walks a half circle around the "Loops" pawn. With LookAtPOI on, the pawn's
target is the walker's head, fed through the sample's own PC_LookAtPOI ("Zone Was Selected").
With it off, the zone is never selected and the Control Rig node's alpha stays off. Nothing is saved.
"""
from pathlib import Path
from datetime import datetime
import json
import math
import re
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/ControlRigLab"
PAWN = "Pawn_LookAt_POI___Loops"        # faces -X at (800, 0)
RADIUS = 220.0
START_ANGLE, END_ANGLE = 100.0, -100.0  # degrees from the pawn's facing; the walker goes from its right to its left
CAMERA = {"location": [360, -420, 380], "look_at": [780, 20, 110], "fov": 52}


def wait_recording(client):
    deadline = time.monotonic() + 300
    while True:
        status = lab(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            lab(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(0.5)


def run_case(client, name, enabled):
    folder = EVIDENCE / name
    if folder.exists():
        target = EVIDENCE / "archive" / (name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        target.parent.mkdir(parents=True, exist_ok=True)
        folder.rename(target)
    restore_editor_window("GameAnimationSample")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
        time.sleep(1.0)
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 1.0}}))
    time.sleep(2.0)
    lab(client, "configure_view")
    angle = math.radians(180.0 + START_ANGLE)
    start = [800.0 + RADIUS * math.cos(angle), RADIUS * math.sin(angle), 100.0]
    lab(client, "poi_setup", {"pawn": PAWN, "target": [start[0], start[1], 165.0], "enabled": enabled, "hide_gizmo": True,
                              "camera": CAMERA})
    lab(client, "poi_walker", {"location": start, "yaw": 180.0, "walk": True})
    time.sleep(2.0)                      # let the pawn settle on the walker before it starts moving
    lab(client, "poi_walk_run", {"case": name, "radius": RADIUS, "end_angle": END_ANGLE, "direction": -1, "duration": 6.0,
                                 "capture": True, "interval": 1 / 30, "capture_time_dilation": 0.2, "start_delay": 0.3,
                                 "setup": {"pawn": PAWN, "radius": RADIUS, "start_angle": START_ANGLE, "end_angle": END_ANGLE,
                                           "lookat_enabled": enabled, "camera": CAMERA}})
    print(name, wait_recording(client), flush=True)


if __name__ == "__main__":
    client = Client()
    lab(client, "close_asset_previews", {"assets": value(client.call(EDITOR, "GetOpenAssets"))})
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    lab(client, "open_level", {"path": "/Game/Levels/LookAtPOI_Level"})
    for name, enabled in (("lookat_on", True), ("lookat_off", False)):
        run_case(client, name, enabled)
    value(client.call(EDITOR, "StopPIE"))
    data = lab(client, "dump_object", {"path": "/Game/IsolatedExamples/LookAtPOI/DA_LookAtPOI__Loops.DA_LookAtPOI__Loops",
                                       "properties": ["System Center Bone", "Root Bone", "LookAt Body Parts", "Foot Fix",
                                                      "Clamp Min Distance", "Fade Out Distance", "Antimeridian Cooldown"]})
    # Blueprint struct fields are exported with GUID suffixes; strip them so the file is readable.
    text = re.sub(r"_\d+_[0-9A-F]{32}", "", json.dumps(data, indent=1))
    (EVIDENCE / "lookat_data_asset.json").write_text(text, encoding="utf-8")
    lab(client, "restore_session", {})
    lab(client, "open_level", {"path": "/Game/Levels/DefaultLevel"})
    print("Trials completed.", flush=True)
