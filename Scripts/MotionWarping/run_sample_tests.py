"""Run the mantle-height trials in GameAnimationSample through Unreal MCP.

The editor must be interactive, started with the MCP server, and have
register_toolset.py executed once (see README.md). Sample assets are never saved.
"""
from pathlib import Path
from datetime import datetime
import argparse
import json
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/MotionWarpingLab"
HEIGHTS = (60, 100, 150)


def camera_for(height):
    # Side view from +Y so the character moves left to right.
    # One fixed camera for every height, so only the block changes between clips.
    return {"x": 10, "y": 760, "z": 230, "look_x": 10, "look_z": 160, "fov": 50}


def cases():
    for height in HEIGHTS:
        for disabled in (True, False):
            yield f"mantle_h{height}_{'off' if disabled else 'on'}", height, disabled, False
    # ON again with the engine's own debug drawing (a.MotionWarping.Debug 2). Not used for numbers.
    for height in (60, 150):
        yield f"debug_h{height}_on", height, False, True


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


def run_case(client, name, height, disabled, debug):
    folder = EVIDENCE / name
    if folder.exists():
        archive = EVIDENCE / "archive" / (name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        archive.parent.mkdir(parents=True, exist_ok=True)
        assert folder.resolve().is_relative_to(EVIDENCE.resolve())
        folder.rename(archive)
    restore_editor_window("GameAnimationSample")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 1.0}}))
    lab(client, "configure_view")
    setup = lab(client, "prepare_mantle", {"height": height, "disabled": disabled, "gap": 85, "camera": camera_for(height),
                                           "engine_debug": 2 if debug else 0, "debug_lifetime": 10.0 if debug else 1.0})
    assert setup["disabled_value"] == int(disabled), setup
    audit = lab(client, "capture_audit")
    assert "UEDPIE_" in audit["world"] and "CameraActor_" in audit["view_target"], audit
    time.sleep(1.0)  # let the spawned character settle on the floor
    lab(client, "start_recording", {"case": name, "duration": 2.6, "interval": 1 / 30, "capture_time_dilation": 0.2})
    status = wait_recording(client)
    print(name, status, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="Run only the named cases, e.g. mantle_h150_off")
    args = parser.parse_args()
    client = Client()
    open_assets = value(client.call(EDITOR, "GetOpenAssets"))
    lab(client, "close_asset_previews", {"assets": open_assets})
    for name, height, disabled, debug in cases():
        if not args.case or name in args.case:
            run_case(client, name, height, disabled, debug)
    montages = {}
    for name, *_ in cases():
        record_path = EVIDENCE / name / "measurements.json"
        if not record_path.exists():
            continue
        for sample in json.loads(record_path.read_text())["samples"]:
            if sample["montage"] and sample["montage"] not in montages:
                montages[sample["montage"]] = lab(client, "inspect_asset", {"asset": sample["montage"]})
    (EVIDENCE / "montages.json").write_text(json.dumps(montages, indent=2), encoding="utf-8")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    lab(client, "restore_session")
    print("Trials completed.", flush=True)
