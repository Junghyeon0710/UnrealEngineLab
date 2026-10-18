"""Play the parkour course in PIE through Unreal MCP and record it.

1. A full run: hold forward, tap Jump in front of each obstacle (the same IA_Move / IA_Jump actions as a keyboard).
   The same run again with the foot placement Control Rig off (a.AnimNode.FootPlacement.Enable 0).
2. A fall test: after checkpoint 1, steer off the plateau to check the respawn.
3. Runs with the Control Rig or Motion Warping debug drawing on, captured around the parts that matter.
   The 30° ramp down filmed from the side (the pawn's own CameraComponent) with the foot placement rig off and on.
4. An editor viewport shot of the whole course.

Every run records the Motion Matching selection, foot heights and Motion Warping targets each tick.

The UnrealEngineLab editor must run the MCP server, have register_toolset.py executed once and
L_ParkourCourse open. The best time saved by earlier runs is cleared first so the finish shows NEW BEST.
"""
from pathlib import Path
from datetime import datetime
import base64
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/ParkourCourseLab"
SAVE_GAME = ROOT / "Saved/SaveGames/ParkourCourse.sav"
JUMP_AT_X = [5685, 6385, 7165, 7700]   # about 2 m before the hurdle, the wall and the two ledges
OVERVIEW = {"location": {"x": -1400, "y": -2600, "z": 2200}, "rotation": {"pitch": -30, "yaw": 45, "roll": 0},
            "scale": {"x": 1, "y": 1, "z": 1}}


def wait_recording(client):
    deadline = time.monotonic() + 900
    while True:
        status = lab(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            lab(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(1.0)


def fresh_pie(client):
    restore_editor_window("UnrealEngineLab")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
        time.sleep(1.5)
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 2.0}}))
    time.sleep(3.0)
    lab(client, "configure_view")
    status = lab(client, "pie_status")
    assert status["game_mode"] == "ParkourGameMode" and status["pawn"] == "SandboxCharacter_Mover_C", status


DEBUG_OFF = {"DDCvar.DrawCharacterDebugShapes": 0, "ControlRig.EnableDrawInterfaceInGame": 0, "a.AnimNode.ControlRig.Debug": 0,
             "a.AnimNode.FootPlacement.Debug": 0, "a.MotionWarping.Debug": 0, "a.MotionWarping.Debug.Target": 0,
             "a.AnimNode.FootPlacement.Enable": 1}
CONTROL_RIG_DEBUG = {"ControlRig.EnableDrawInterfaceInGame": 1, "a.AnimNode.ControlRig.Debug": 1, "a.AnimNode.FootPlacement.Debug": 1}
# 1 only logs; 2 draws the original root motion path and the warped one. Debug.Target 2 draws the warp targets.
MOTION_WARPING_DEBUG = {"a.MotionWarping.Debug": 2, "a.MotionWarping.Debug.Target": 2}


def record(client, name, options, cvars=None, capture=True, interval=1 / 15):
    folder = EVIDENCE / name
    if folder.exists():
        archive = EVIDENCE / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        folder.rename(archive / (name + "_" + datetime.now().strftime("%Y%m%d_%H%M%S")))
    fresh_pie(client)
    lab(client, "console", {"cvars": dict(DEBUG_OFF, **(cvars or {}))})
    lab(client, "autoplay", dict(options, case=name, detail=True, capture=capture, interval=interval,
                                 capture_time_dilation=0.25 if capture else 1.0))
    print(name, wait_recording(client)["samples"], flush=True)


if __name__ == "__main__":
    client = Client()
    if SAVE_GAME.exists():
        SAVE_GAME.unlink()
    run = {"jump_at_x": JUMP_AT_X, "duration": 45, "steer_y": 0, "stop_after_finish": 3.0}
    # The run shown in the GIFs, and the same run with the foot placement Control Rig switched off.
    record(client, "run_capture", run)
    record(client, "run_foot_placement_off", run, cvars={"a.AnimNode.FootPlacement.Enable": 0}, capture=False)
    # Falling off the plateau after checkpoint 1.
    record(client, "fall_capture", {"jump_at_x": [], "duration": 16, "steer_y": 0, "steer_plan": [[2900, 700]]})
    # Each system's own debug drawing in the player's view, captured only around the parts that matter.
    record(client, "debug_control_rig", dict(run, capture_windows=[[6.5, 7.5], [12.4, 13.6]]), cvars=CONTROL_RIG_DEBUG)
    record(client, "debug_motion_warping", dict(run, capture_windows=[[17.0, 18.4], [20.9, 22.4]]), cvars=MOTION_WARPING_DEBUG)
    # Motion Matching node debug text around the start and the hurdle. The text is on the debug canvas, so Shot needs showui.
    record(client, "debug_motion_matching", dict(run, duration=19.0, capture_ui=True, capture_windows=[[0.0, 3.3], [16.9, 18.7]]),
           cvars={"a.AnimNode.MotionMatching.DebugDrawInfo": 1})
    # One plain jump on the start floor (no obstacle ahead), filmed from the side with the same debug text.
    record(client, "debug_mm_jump", {"jump_at_x": [800], "duration": 6.5, "steer_y": 0, "capture_ui": True,
                                     "side_camera": {"from_x": -1000, "offset": [0, -520, 30], "pitch": -3, "fov": 60},
                                     "capture_windows": [[3.3, 5.8]]},
           cvars={"a.AnimNode.MotionMatching.DebugDrawInfo": 1, "r.MotionBlurQuality": 0})
    lab(client, "console", {"cvars": {"a.AnimNode.MotionMatching.DebugDrawInfo": 0, "r.MotionBlurQuality": 4}})
    # The 30° ramp down filmed from the side with the foot placement Control Rig off and on. Motion blur off so the feet stay sharp.
    side = {"from_x": 2900, "offset": [0, -430, 5], "pitch": 0, "fov": 50}
    for state in (1, 0):
        record(client, "side_ramp_down_rig_" + ("on" if state else "off"),
               dict(run, duration=12.8, side_camera=side, capture_windows=[[9.9, 12.5]]),
               cvars={"a.AnimNode.FootPlacement.Enable": state, "r.MotionBlurQuality": 0}, interval=1 / 30)
    lab(client, "console", {"cvars": {"r.MotionBlurQuality": 4}})
    lab(client, "console", {"cvars": DEBUG_OFF})
    value(client.call(EDITOR, "StopPIE"))
    lab(client, "restore_session")
    time.sleep(5.0)  # right after PIE stops the editor viewport has not redrawn the course yet
    shot = value(client.call(EDITOR, "CaptureViewport", {"captureTransform": OVERVIEW, "bShowUI": False,
                                                          "annotations": {"gridSpacing": 0, "gridExtent": 0, "gridHeight": 0,
                                                                          "maxLabelDistance": 0}}))
    (EVIDENCE / "course_overview.png").write_bytes(base64.b64decode(shot["image"]["data"]))
    print("Trials completed.", flush=True)
