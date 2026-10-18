"""Run the Motion Matching trials in GameAnimationSample through Unreal MCP.

The editor must be interactive, started with the MCP server, and have register_toolset.py
executed once (see README.md). Sample assets are never saved.
"""
from pathlib import Path
from datetime import datetime
import argparse
import json
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/MotionMatchingLab"
# Idle 0.5s, run along +X, reverse the input at 2.3s, let go at 3.6s.
SEGMENTS = [[0.5, 2.3, 0.0, 1.0], [2.3, 3.6, 180.0, 1.0]]
CAMERA = {"dx": 0.0, "dy": 580.0, "z": 190.0, "look_dx": 0.0, "look_z": 85.0, "fov": 50.0}
MODES = {
    "dense": {"database_lod": 0},
    "sparse": {"database_lod": 1},
    "xsparse": {"database_lod": 2},
    "sm": {"state_machine": True},
}
REPEATS = 3


def cases():
    for mode in MODES:
        yield f"mm_{mode}", mode, True          # captured run for the GIFs
    for mode in MODES:
        for i in range(1, REPEATS + 1):
            yield f"mm_{mode}_r{i}", mode, False  # measurement runs


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
        time.sleep(0.5)


def run_case(client, name, mode, capture):
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
    options = dict(MODES[mode], camera=CAMERA, debug_shapes=capture)
    setup = lab(client, "prepare_run", options)
    audit = lab(client, "capture_audit")
    assert "UEDPIE_" in audit["world"] and "CameraActor_" in audit["view_target"], audit
    time.sleep(1.0)  # let the spawned character settle into idle
    lab(client, "start_run", {"case": name, "segments": SEGMENTS, "duration": 5.0, "capture": capture,
                              "interval": 1 / 30, "capture_time_dilation": 0.2})
    print(name, setup["read_back"], wait_recording(client), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", action="append", help="Run only the named cases, e.g. mm_dense or mm_sm_r2")
    args = parser.parse_args()
    client = Client()
    open_assets = value(client.call(EDITOR, "GetOpenAssets"))
    lab(client, "close_asset_previews", {"assets": open_assets})
    for name, mode, capture in cases():
        if not args.case or name in args.case:
            run_case(client, name, mode, capture)
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
    schema = lab(client, "inspect_schema", {"path": "/Game/Characters/UEFN_Mannequin/Animations/MotionMatchingData/Schemas/PSS_Default"})
    (EVIDENCE / "schema.json").write_text(json.dumps(schema, indent=1), encoding="utf-8")
    lab(client, "restore_session")
    print("Trials completed.", flush=True)
