"""Run the combat (attack toward an enemy) trials in the UnrealEngineLab project through Unreal MCP.

Needs the template mannequin in Content/Characters/Mannequins and register_toolset.py executed
once in the editor (see README.md). Creates /Game/MotionWarpingLab/AM_Attack_MotionWarping and
the MotionWarpingCombat test map if they do not exist.
"""
from pathlib import Path
from datetime import datetime
import argparse
import json
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/MotionWarpingLab"
ATTACK = "/Game/Characters/Mannequins/Anims/Unarmed/Attack/MM_Attack_02"
# MM_Attack_02 ends with a left hook at 0.467s; the hand is then 99cm ahead of the root.
WINDOW = (0.05, 0.4667)
REACH = 124.0  # root stops this far from the enemy centre so the fist meets the front of the body (25cm)
CAMERA = {"x": 10, "y": -240, "z": 520, "look_x": 95, "look_y": 75, "look_z": 40, "fov": 55}
TOP_CAMERA = {"x": 105, "y": 60, "z": 640, "look_x": 105, "look_y": 61, "look_z": 0, "fov": 55}
CASES = [
    # name, enemy distance, enemy angle (deg, + is to the attacker's left), disabled, engine debug
    ("combat_far_off", 260, 35, True, False), ("combat_far_on", 260, 35, False, False),
    ("combat_side_off", 140, 60, True, False), ("combat_side_on", 140, 60, False, False),
]


def wait_recording(client):
    deadline = time.monotonic() + 120
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


def run_case(client, name, distance, angle, disabled, debug):
    folder = EVIDENCE / name
    if folder.exists():
        archive = EVIDENCE / "archive" / (name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        archive.parent.mkdir(parents=True, exist_ok=True)
        assert folder.resolve().is_relative_to(EVIDENCE.resolve())
        folder.rename(archive)
    restore_editor_window("UnrealEngineLab")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 1.0}}))
    lab(client, "configure_view")
    setup = lab(client, "combat_prepare", {"distance": distance, "angle": angle, "disabled": disabled, "reach": REACH,
                                           "camera": TOP_CAMERA if debug else CAMERA,
                                           "engine_debug": 2 if debug else 0, "debug_lifetime": 10.0 if debug else 1.0})
    assert setup["has_warping"] and setup["disabled_value"] == int(disabled), setup
    time.sleep(1.0)
    lab(client, "combat_start", {"case": name, "duration": 2.0, "interval": 1 / 30, "capture_time_dilation": 0.2})
    print(name, wait_recording(client), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="Run only the named cases, e.g. combat_far_on")
    args = parser.parse_args()
    client = Client()
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    lab(client, "combat_open_map")
    montage = lab(client, "combat_build_montage", {"source": ATTACK, "start": WINDOW[0], "end": WINDOW[1]})
    (EVIDENCE / "combat_montage.json").write_text(json.dumps(montage, indent=2), encoding="utf-8")
    for name, distance, angle, disabled, debug in CASES:
        if not args.case or name in args.case:
            run_case(client, name, distance, angle, disabled, debug)
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    lab(client, "restore_session")
    print("Combat trials completed.", flush=True)
