"""Named actions for the GameplayMessage lab toolset (Docs/UE/GameplayMessage.md). Runs inside the editor's Python.

Every action works on the PIE world of L_GameplayMessageLab, whose game mode is AGMLabGameMode.
"""
from pathlib import Path
import json
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/GameplayMessageLab"
STATE = getattr(unreal, "_gm_lab_state", {})
unreal._gm_lab_state = STATE
GAME_MODE_CALLS = {"start_demo", "reset_counters", "run_order_test", "run_mismatch_test", "run_benchmark"}


def _game_world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE first")
    return world


def _game_mode(world=None):
    mode = unreal.GameplayStatics.get_game_mode(world or _game_world())
    if not mode or mode.get_class().get_name() != "GMLabGameMode":
        raise RuntimeError("PIE is not running L_GameplayMessageLab (game mode %s)" % (mode.get_class().get_name() if mode else None))
    return mode


def _call(mode, function, args):
    if function not in GAME_MODE_CALLS:
        raise ValueError("Not allowed: " + function)
    return getattr(mode, function)(*args)


def pie_status(options):
    mode = _game_mode()
    return {"game_mode": mode.get_class().get_name(), "counters": json.loads(mode.get_counters_json())}


def call(options):
    """Call one game mode function. The order, mismatch and benchmark tests return JSON."""
    mode = _game_mode()
    returned = _call(mode, options["function"], options.get("args", []))
    out = {"counters": json.loads(mode.get_counters_json())}
    if isinstance(returned, str) and returned:
        out["returned"] = json.loads(returned)
    return out


def configure_view(options):
    """Steady frame rate while recording, even with the editor in the background."""
    unreal.SystemLibrary.execute_console_command(_game_world(), "t.MaxFPS %d" % int(options.get("fps", 30)))
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    STATE.setdefault("original_throttle", settings.get_editor_property("bThrottleCPUWhenNotForeground"))
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    return {"fps": int(options.get("fps", 30))}


def console(options):
    """Only the message log switch of the plugin."""
    command = options["command"]
    if command not in ("GameplayMessageSubsystem.LogMessages 1", "GameplayMessageSubsystem.LogMessages 0"):
        raise ValueError("Not allowed: " + command)
    unreal.SystemLibrary.execute_console_command(_game_world(), command)
    return {"command": command}


def restore_session(options):
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if "original_throttle" in STATE:
        settings.set_editor_property("bThrottleCPUWhenNotForeground", STATE["original_throttle"])
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "t.MaxFPS 0")
    return {"restored": True}


def open_asset(options):
    path = options["path"]
    if not path.startswith("/Game/GameplayMessageLab/"):
        raise ValueError("Only lab assets")
    asset = unreal.load_asset(path)
    unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).open_editor_for_assets([asset])
    return {"opened": path}


def record(options):
    """Sample the counters every tick, run timed game mode calls, and capture the editor window at an interval.

    options: case, duration, interval, capture_windows [[t0, t1]], actions [[t, function, args]].
    Frames are 'Shot showui' captures of the whole editor window, because UMG and the HUD draw on top of the viewport.
    """
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    mode = _game_mode(world)
    name = options["case"]
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob("frame_*.png"):
        old.unlink()
    duration = float(options.get("duration", 10.0))
    interval = float(options.get("interval", 0.2))
    windows = options.get("capture_windows")
    actions = sorted(options.get("actions", []), key=lambda a: a[0])
    start = unreal.GameplayStatics.get_time_seconds(world)
    record = {"case": name, "options": options, "samples": [], "frames": [], "actions": []}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "pending": None, "next_action": 0})

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        (directory / "measurements.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start
            while STATE["next_action"] < len(actions) and t >= actions[STATE["next_action"]][0]:
                at, function, *rest = actions[STATE["next_action"]]
                _call(mode, function, rest[0] if rest else [])
                record["actions"].append({"t": t, "function": function})
                STATE["next_action"] += 1
            record["samples"].append(dict(json.loads(mode.get_counters_json()), t=t))
            pending = STATE["pending"]
            ready = pending is None or pending.exists()
            in_window = not windows or any(w0 <= t <= w1 for w0, w1 in windows)
            if options.get("capture", True) and in_window and ready and t >= STATE["next_capture"]:
                filename = "frame_%04d.png" % len(record["frames"])
                STATE["pending"] = directory / filename
                unreal.SystemLibrary.execute_console_command(
                    world, 'Shot showui filename="%s" -nosuffix' % STATE["pending"].as_posix())
                record["frames"].append({"file": filename, "t": t})
                STATE["next_capture"] = t + interval
            if t >= duration and ready:
                finish()
        except Exception:
            record["error"] = traceback.format_exc()
            finish()

    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory)}


def recording_status(options):
    record = STATE.get("record", {})
    return {"recording": STATE.get("recording", False), "frames": len(record.get("frames", [])),
            "samples": len(record.get("samples", [])), "error": record.get("error")}


def abort_recording(options):
    if STATE.get("callback"):
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
    STATE["recording"] = False
    return {"recording": False}


def dispatch(action, options):
    actions = {"pie_status": pie_status, "call": call, "configure_view": configure_view, "console": console,
               "restore_session": restore_session, "open_asset": open_asset, "record": record,
               "recording_status": recording_status, "abort_recording": abort_recording}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    try:
        return actions[action](options)
    except Exception:
        return {"error": traceback.format_exc()}
