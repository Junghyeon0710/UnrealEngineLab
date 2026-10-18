"""Named Unreal MCP operations for the Motion Matching article.

Runs inside the GameAnimationSample editor and is reached only through
register_toolset.py -> MotionMatchingLabToolset.run_action.
Everything it spawns lives in the disposable PIE world. Nothing is saved.
"""
from pathlib import Path
import json
import math
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/MotionMatchingLab"
STATE = getattr(unreal, "_motion_matching_lab_state", {})
unreal._motion_matching_lab_state = STATE

CMC_CHARACTER = "/Game/Blueprints/SandboxCharacter_CMC.SandboxCharacter_CMC_C"
# Empty floor in DefaultLevel, south of the traversal course.
RUNWAY = (1200.0, -7500.0)
FEET = ("ball_l", "ball_r")
# Blueprint variables of SandboxCharacter_CMC_ABP, read by their exact names.
ANIM_VARIABLES = ("CurrentSelectedDatabase", "CurrentSelectedAnim", "Search Cost", "Gait", "Speed2D",
                  "UseExperimentalStateMachine", "MMDatabaseLOD", "StateMachineState")


def _editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _game_world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE first")
    return world


def _vector(vector):
    return [vector.x, vector.y, vector.z]


def _name(value):
    if value is None:
        return None
    if isinstance(value, unreal.Object):
        return value.get_name()
    return str(value)


def _spawn(world, cls, transform):
    # BeginDeferredActorSpawnFromClass has no Python glue; call the reflected UFunction.
    library = unreal.get_default_object(unreal.GameplayStatics)
    scale_method = unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor = library.call_method("BeginDeferredActorSpawnFromClass", args=(world, cls, transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale_method))
    library.call_method("FinishSpawningActor", args=(actor, transform, scale_method))
    return actor


def api_info(options):
    cls = getattr(unreal, options["class"])
    return {"class": options["class"], "members": [m for m in dir(cls) if not m.startswith("_")],
            "docs": {m: str(getattr(cls, m).__doc__) for m in options.get("methods", [])}}


def inspect_object(options):
    """Read named editor properties of any loaded object (assets, sub-objects)."""
    obj = unreal.load_object(None, options["path"])
    if not obj:
        raise RuntimeError("Object not found")
    result = {"path": obj.get_path_name(), "class": obj.get_class().get_name()}
    for prop in options.get("properties", []):
        try:
            result[prop] = str(obj.get_editor_property(prop))
        except Exception as error:
            result[prop] = {"error": str(error)}
    return result


def inspect_schema(options):
    """Trajectory samples and pose sub-channels of a Pose Search Schema."""
    schema = unreal.load_asset(options["path"])
    result = {"path": schema.get_path_name(), "sample_rate": schema.get_editor_property("sample_rate"),
              "data_preprocessor": str(schema.get_editor_property("data_preprocessor")), "channels": []}

    def read(obj, names):
        out = {"class": obj.get_class().get_name()}
        for name in names:
            try:
                value = obj.get_editor_property(name)
                out[name] = str(value) if not isinstance(value, (int, float, bool)) else value
            except Exception:
                pass
        return out

    for channel in schema.get_editor_property("channels"):
        entry = read(channel, ["weight", "sample_time_offset", "input_query_pose", "use_blue_print_query_override"])
        if isinstance(channel, unreal.PoseSearchFeatureChannel_Trajectory):
            entry["samples"] = [{"offset": s.get_editor_property("offset"), "flags": s.get_editor_property("flags"),
                                 "weight": s.get_editor_property("weight")} for s in channel.get_editor_property("samples")]
        if isinstance(channel, unreal.PoseSearchFeatureChannel_Group):
            entry["sub_channels"] = []
            for sub in channel.get_editor_property("sub_channels"):
                item = read(sub, ["weight", "sample_time_offset", "origin_time_offset", "use_character_space_velocities"])
                try:
                    item["bone"] = str(sub.get_editor_property("bone").get_editor_property("bone_name"))
                except Exception:
                    pass
                entry["sub_channels"].append(item)
        result["channels"].append(entry)
    return result


def close_asset_previews(options):
    subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    closed = []
    for path in options.get("assets", []):
        asset = unreal.load_object(None, path)
        if asset:
            closed.append({"path": path, "editors": subsystem.close_all_editors_for_asset(asset)})
    return {"closed_without_saving": closed}


def configure_view(options):
    world = _game_world()
    commands = ["t.MaxFPS 30", "r.Streaming.PoolSize 1000"]
    for command in commands:
        unreal.SystemLibrary.execute_console_command(world, command)
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    STATE.setdefault("original_throttle", settings.get_editor_property("bThrottleCPUWhenNotForeground"))
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    return {"session_only_commands": commands}


def _anim_values(anim):
    values = {}
    for key in ANIM_VARIABLES:
        try:
            values[key] = anim.get_editor_property(key)
        except Exception:
            continue
    try:
        # In the experimental state machine mode the AnimBP plays BlendStackInputs.Anim instead of a search result.
        values["BlendStackAnim"] = anim.get_editor_property("BlendStackInputs").get_editor_property("Anim")
    except Exception:
        pass
    for key in ("CurrentSelectedDatabase", "CurrentSelectedAnim", "BlendStackAnim"):
        if key in values:
            values[key] = _name(values[key])
    try:
        # Databases the chooser handed to the Motion Matching node this frame.
        values["ValidDatabases"] = [_name(db) for db in anim.get_editor_property("ValidDatabases")]
    except Exception:
        pass
    for key in ("Gait", "StateMachineState"):
        if key in values:
            values[key] = str(values[key]).split(".")[-1].split(":")[0]
    return values


def _future_trajectory(anim):
    """Predicted part of the AnimBP's Trajectory (TimeInSeconds > 0)."""
    samples = anim.get_editor_property("Trajectory").get_editor_property("samples")
    return [[s.get_editor_property("time_in_seconds")] + _vector(s.get_editor_property("position"))
            for s in samples if s.get_editor_property("time_in_seconds") > 0.0]


def prepare_run(options):
    """Spawn a CMC sandbox character on the runway, set the GASP CVars and a follow camera."""
    world = _game_world()
    start = unreal.Vector(RUNWAY[0], RUNWAY[1], 92.0)
    character = _spawn(world, unreal.load_class(None, CMC_CHARACTER), unreal.Transform(location=start, rotation=unreal.Rotator(0, 0, 0)))
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    old_pawn = controller.get_controlled_pawn()
    controller.possess(character)
    if old_pawn and old_pawn != character:
        old_pawn.set_actor_hidden_in_game(True)
        old_pawn.set_actor_enable_collision(False)

    # GASP starts in strafe mode (faces the controller). Turn it off so the character faces its movement.
    input_state = character.get_editor_property("CharacterInputState")
    for field, value in (("WantsToStrafe", bool(options.get("strafe", False))), ("WantsToSprint", bool(options.get("sprint", False))),
                         ("WantsToWalk", bool(options.get("walk", False)))):
        try:
            input_state.set_editor_property(field, value)
        except Exception:
            pass
    character.set_editor_property("CharacterInputState", input_state)

    cvars = {"DDCvar.MMDatabaseLOD": int(options.get("database_lod", 0)),
             # The AnimBP sets UseExperimentalStateMachine from both CVars; LocomotionSetupCMC is applied last.
             "DDCVar.ExperimentalStateMachine.Enable": int(bool(options.get("state_machine", False))),
             "DDCVar.LocomotionSetupCMC": int(bool(options.get("state_machine", False))),
             # GASP's own debug drawing: trajectory and character shapes as world-space lines.
             "DDCvar.DrawCharacterDebugShapes": int(bool(options.get("debug_shapes", False)))}
    for name, value in cvars.items():
        unreal.SystemLibrary.execute_console_command(world, f"{name} {value}")

    cam = options.get("camera", {"dx": 0.0, "dy": 650.0, "z": 210.0, "look_dx": 0.0, "look_z": 90.0, "fov": 55.0})
    camera = _spawn(world, unreal.CameraActor, unreal.Transform(location=start))
    component = camera.get_component_by_class(unreal.CameraComponent)
    component.set_field_of_view(float(cam.get("fov", 55.0)))
    component.set_constraint_aspect_ratio(False)
    controller.set_view_target_with_blend(camera, 0.0)
    STATE.update({"character": character, "camera": camera, "camera_offset": cam})
    _follow_camera()
    STATE["case_setup"] = {"start": _vector(start), "cvars": cvars, "camera": cam}
    return {"character": character.get_path_name(), "camera": camera.get_path_name(), "cvars": cvars,
            "read_back": {name: unreal.SystemLibrary.get_console_variable_int_value(name) for name in cvars}}


def _follow_camera():
    character, camera, cam = STATE["character"], STATE["camera"], STATE["camera_offset"]
    target = character.get_actor_location()
    if cam.get("fixed"):
        anchor = unreal.Vector(*cam["fixed"])
    else:
        anchor = target
    location = unreal.Vector(anchor.x + cam.get("dx", 0.0), anchor.y + cam.get("dy", 650.0), cam.get("z", 210.0))
    look = unreal.Vector(anchor.x + cam.get("look_dx", 0.0), anchor.y, cam.get("look_z", 90.0))
    camera.set_actor_location_and_rotation(location, unreal.MathLibrary.find_look_at_rotation(location, look), False, True)


def capture_audit(options):
    world = _game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    return {"world": world.get_path_name(), "pawn": unreal.GameplayStatics.get_player_pawn(world, 0).get_path_name(),
            "view_target": pc.get_view_target().get_path_name()}


def _capture(path):
    unreal.SystemLibrary.execute_console_command(_game_world(), f'Shot filename="{path.as_posix()}" -nosuffix')


def capture_frame(options):
    name = options.get("name", "capture")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Use an alphanumeric image name")
    path = EVIDENCE / (name + ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    _capture(path)
    return {"path": str(path)}


def start_run(options):
    """Feed a fixed movement-input script every tick and record what Motion Matching picks."""
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    character = STATE["character"]
    name = options.get("case", "run")
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    # Each segment: [start, end, yaw in degrees, input scale]. Outside segments there is no input.
    segments = options.get("segments", [[0.5, 2.3, 0.0, 1.0], [2.3, 3.6, 180.0, 1.0]])
    duration = float(options.get("duration", 5.0))
    interval = float(options.get("interval", 1 / 30))
    dilation = float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "setup": STATE.get("case_setup"), "segments": segments, "capture_time_dilation": dilation,
              "samples": [], "frames": []}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "capture_path": None})

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            input_yaw = None
            for begin, end, yaw, scale in segments:
                if begin <= t < end:
                    rad = math.radians(yaw)
                    character.add_movement_input(unreal.Vector(math.cos(rad), math.sin(rad), 0.0), float(scale), False)
                    input_yaw = yaw
            _follow_camera()
            anim = character.mesh.get_anim_instance()
            sample = {"t": t, "input_yaw": input_yaw, "location": _vector(character.get_actor_location()),
                      "velocity": _vector(character.get_velocity()), "yaw": character.get_actor_rotation().yaw,
                      "feet": {b: _vector(character.mesh.get_socket_location(b)) for b in FEET}}
            sample.update(_anim_values(anim))
            if len(record["samples"]) % int(options.get("trajectory_every", 3)) == 0:
                sample["future"] = _future_trajectory(anim)
            record["samples"].append(sample)
            pending = STATE.get("capture_path")
            ready = pending is None or pending.exists()
            if capture and t >= STATE["next_capture"] and t < duration and ready:
                filename = f"frame_{len(record['frames']):04d}.png"
                STATE["capture_path"] = directory / filename
                _capture(STATE["capture_path"])
                record["frames"].append({"file": filename, "t": t})
                STATE["next_capture"] = t + interval
            if t >= duration and ready:
                finish()
        except Exception:
            record["error"] = traceback.format_exc()
            finish()

    unreal.GameplayStatics.set_game_paused(world, False)
    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory), "duration": duration}


def recording_status(options):
    record = STATE.get("record", {})
    return {"recording": STATE.get("recording", False), "case": record.get("case"), "frames": len(record.get("frames", [])),
            "samples": len(record.get("samples", [])), "error": record.get("error"),
            "last_t": record["samples"][-1]["t"] if record.get("samples") else None}


def abort_recording(options):
    if STATE.get("callback"):
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
    STATE["recording"] = False
    return {"recording": False}


def restore_session(options):
    if STATE.get("recording"):
        raise RuntimeError("Finish the recording before restoring the session")
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if "original_throttle" in STATE:
        settings.set_editor_property("bThrottleCPUWhenNotForeground", STATE["original_throttle"])
    world = _editor_world()
    for command in ("DDCvar.MMDatabaseLOD 0", "DDCVar.ExperimentalStateMachine.Enable 0", "DDCVar.LocomotionSetupCMC 0",
                    "DDCvar.DrawCharacterDebugShapes 0", "t.MaxFPS 0"):
        unreal.SystemLibrary.execute_console_command(world, command)
    return {"restored": True}


def probe_character(options):
    """Read character properties by exact Blueprint name (debugging)."""
    character = STATE["character"]
    result = {}
    for name in options.get("names", []):
        try:
            result[name] = str(character.get_editor_property(name))
        except Exception as error:
            result[name] = "ERR " + str(error)[:120]
    movement = character.get_component_by_class(unreal.CharacterMovementComponent)
    result["orient_rotation_to_movement"] = movement.get_editor_property("orient_rotation_to_movement")
    result["use_controller_desired_rotation"] = movement.get_editor_property("use_controller_desired_rotation")
    result["use_controller_rotation_yaw"] = character.get_editor_property("use_controller_rotation_yaw")
    return result


def probe_anim(options):
    """Try reading AnimBP variables under several spellings (debugging the Python names)."""
    anim = STATE["character"].mesh.get_anim_instance()
    result = {"class": anim.get_class().get_path_name()}
    inputs = anim.get_editor_property("BlendStackInputs")
    for field in options.get("blend_stack_fields", []):
        try:
            result["BlendStackInputs." + field] = str(inputs.get_editor_property(field))
        except Exception as error:
            result["BlendStackInputs." + field] = "ERR " + str(error)[:80]
    for name in options.get("names", []):
        try:
            result[name] = str(anim.get_editor_property(name))
        except Exception as error:
            result[name] = "ERR " + str(error)[:120]
    return result


def dispatch(action, options):
    actions = {"api_info": api_info, "inspect_object": inspect_object, "close_asset_previews": close_asset_previews,
               "configure_view": configure_view, "prepare_run": prepare_run, "capture_audit": capture_audit,
               "capture_frame": capture_frame, "start_run": start_run, "recording_status": recording_status,
               "abort_recording": abort_recording, "restore_session": restore_session, "probe_anim": probe_anim,
               "probe_character": probe_character, "inspect_schema": inspect_schema}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    result = actions[action](options)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (action + "_latest.json")).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result
