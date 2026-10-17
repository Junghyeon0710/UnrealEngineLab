"""Named, inspectable Unreal MCP operations for the Motion Warping article.

This module runs inside the interactive GameAnimationSample editor.
It never executes source supplied as a tool argument.
"""
from pathlib import Path
import json
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/MotionWarpingLab"
STATE = getattr(unreal, "_motion_warping_lab_state", {})
unreal._motion_warping_lab_state = STATE


def inventory(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folder = options.get("folder", "/Game/Characters/UEFN_Mannequin/Animations/Traversal")
    assets = registry.get_assets_by_path(folder, recursive=True)
    return {
        "project": unreal.Paths.get_project_file_path(),
        "world": world.get_path_name(),
        "assets": [{"path": str(a.package_name), "class": str(a.asset_class_path.asset_name)} for a in assets],
    }


def inspect_asset(options):
    asset = unreal.load_asset(options["asset"])
    if not asset:
        raise RuntimeError("Asset not found")
    result = {"path": asset.get_path_name(), "class": asset.get_class().get_name()}
    for prop in options.get("properties", []):
        try:
            result[prop] = str(asset.get_editor_property(prop))
        except Exception as error:
            result[prop] = {"error": str(error)}
    if isinstance(asset, unreal.AnimMontage):
        result["windows"] = []
        for window in unreal.MotionWarpingUtilities.get_motion_warping_windows_from_animation(asset):
            state = window.get_editor_property("anim_notify")
            entry = {"start": window.get_editor_property("start_time"), "end": window.get_editor_property("end_time"), "state": state.get_path_name() if state else None}
            if state:
                entry["state_class"] = state.get_class().get_name()
                try:
                    modifier = state.get_editor_property("root_motion_modifier")
                    entry["modifier"] = modifier.get_class().get_name() if modifier else None
                    entry["modifier_path"] = modifier.get_path_name() if modifier else None
                    if modifier:
                        for key in ["warp_target_name", "warp_translation", "ignore_z_axis", "warp_rotation", "warp_point_anim_provider", "warp_point_anim_bone_name"]:
                            try:
                                entry[key] = str(modifier.get_editor_property(key))
                            except Exception:
                                pass
                except Exception:
                    pass
            result["windows"].append(entry)
    return result


def api_info(options):
    cls = getattr(unreal, options["class"])
    return {"class": options["class"], "members": [m for m in dir(cls) if not m.startswith("_")],
            "docs": {m: str(getattr(cls, m).__doc__) for m in options.get("methods", [])}}


def inspect_actors(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() if options.get("pie") else unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
    result = []
    for actor in actors:
        if options.get("filter", "").lower() not in (actor.get_name()+actor.get_class().get_name()).lower():
            continue
        center, extent = actor.get_actor_bounds(True)
        row = {"path": actor.get_path_name(), "class": actor.get_class().get_name(), "location": str(actor.get_actor_location()), "rotation": str(actor.get_actor_rotation()),
               "bounds_center": [center.x, center.y, center.z], "bounds_extent": [extent.x, extent.y, extent.z]}
        if options.get("components"):
            row["components"] = [{"path": c.get_path_name(), "class": c.get_class().get_name()} for c in actor.get_components_by_class(unreal.ActorComponent)]
        result.append(row)
    return {"world": world.get_path_name() if world else None, "actors": result}


def player_info(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    actor = unreal.GameplayStatics.get_player_pawn(world, 0)
    if not actor:
        return {"world": str(world), "player": None}
    result = {"world": world.get_path_name(), "player": actor.get_path_name(), "location": str(actor.get_actor_location()), "rotation": str(actor.get_actor_rotation()),
              "components": [{"name": c.get_name(), "class": c.get_class().get_name(), "path": c.get_path_name()} for c in actor.get_components_by_class(unreal.ActorComponent)]}
    try:
        inputs = actor.call_method("GetTraversalCheckInputs")
        result["inputs"] = str(inputs)
    except Exception as e:
        result["inputs_error"] = str(e)
    if isinstance(actor, unreal.Character):
        mesh = actor.mesh
        result["mesh"] = {"asset": str(mesh.get_skeletal_mesh_asset()), "visible": mesh.is_visible(), "hidden": mesh.get_editor_property("hidden_in_game"), "anim_instance": str(mesh.get_anim_instance())}
    return result


def prepare_case(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE first")
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    location = unreal.Vector(*options.get("start", [2330.0, -2400.0, 90.0]))
    rotation = unreal.Rotator(0, float(options.get("yaw", 0)), 0)
    character_class = unreal.load_class(None, "/Game/Blueprints/SandboxCharacter_CMC.SandboxCharacter_CMC_C")
    transform = unreal.Transform(location=location, rotation=rotation)
    # These two Blueprint-internal functions have no Python glue; call their
    # reflected UFunctions using the signatures in GameplayStatics.h.
    library = unreal.get_default_object(unreal.GameplayStatics)
    scale_method = unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    character = library.call_method("BeginDeferredActorSpawnFromClass", args=(world, character_class, transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale_method))
    library.call_method("FinishSpawningActor", args=(character, transform, scale_method))
    controller.possess(character)
    unreal.SystemLibrary.execute_console_command(world, "a.MotionWarping.Disable " + str(int(options.get("disabled", False))))
    unreal.SystemLibrary.execute_console_command(world, "t.MaxFPS 30")
    camera_location = unreal.Vector(location.x + 120, location.y - 530, 230)
    look_at = unreal.Vector(location.x + 120, location.y, 95)
    camera_rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, look_at)
    camera_transform = unreal.Transform(location=camera_location, rotation=camera_rotation)
    camera = library.call_method("BeginDeferredActorSpawnFromClass", args=(world, unreal.CameraActor, camera_transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale_method))
    library.call_method("FinishSpawningActor", args=(camera, camera_transform, scale_method))
    camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(50.0)
    controller.set_view_target_with_blend(camera, 0.0)
    STATE["camera"] = camera
    subject_name = "LevelBlock_Traversable_C_4" if abs(location.y + 2400) < 1 else "LevelBlock_Traversable_C_7"
    hidden = []
    subject = None
    for block in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if not block.get_class().get_name().startswith("LevelBlock"):
            continue
        if block.get_name() == subject_name:
            subject = block
        # Presentation only, in the disposable PIE world. Collision stays enabled.
        if block.get_name() not in (subject_name, "LevelBlock_C_1"):
            block.set_actor_hidden_in_game(True)
            hidden.append(block.get_name())
    center, extent = subject.get_actor_bounds(True)
    STATE["case_setup"] = {"subject": subject.get_path_name(), "bounds_center": _vector(center),
                           "bounds_extent": _vector(extent), "hidden_background_blocks": hidden,
                           "camera_location": _vector(camera_location), "camera_look_at": _vector(look_at), "camera_fov": 50.0}
    return {"character": character.get_path_name(), "camera": camera.get_path_name(), "start": str(character.get_actor_location()), "disabled": options.get("disabled", False),
            "disabled_value": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable")}


def close_asset_previews(options):
    subsystem = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
    closed = []
    for path in options.get("assets", []):
        asset = unreal.load_object(None, path)
        if asset:
            closed.append({"path": path, "editors": subsystem.close_all_editors_for_asset(asset)})
    return {"closed_without_saving": closed}


def capture_audit(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    manager = unreal.GameplayStatics.get_player_camera_manager(world, 0)
    return {"world": world.get_path_name(), "pawn": unreal.GameplayStatics.get_player_pawn(world, 0).get_path_name(),
            "view_target": pc.get_view_target().get_path_name(),
            "camera_location": _vector(manager.get_camera_location()),
            "camera_rotation": str(manager.get_camera_rotation()),
            "camera_fov": manager.get_fov_angle()}


def configure_view(options):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    commands = ["sg.TextureQuality 1", "sg.ShadowQuality 1", "sg.GlobalIlluminationQuality 1", "sg.ReflectionQuality 1", "r.Streaming.PoolSize 1000"]
    for command in commands:
        unreal.SystemLibrary.execute_console_command(world, command)
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    STATE.setdefault("original_throttle", settings.get_editor_property("bThrottleCPUWhenNotForeground"))
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    return {"session_only_commands": commands}


def _vector(vector):
    return [vector.x, vector.y, vector.z]


def _capture(path):
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE before requesting a game viewport capture")
    unreal.SystemLibrary.execute_console_command(world, f'Shot filename="{path.as_posix()}" -nosuffix')


def _draw_measurement_points(world, point, targets):
    """Native Unreal debug geometry at measured world positions, not an image edit."""
    foreground = unreal.DrawDebugSceneDepthPriorityGroup.FOREGROUND
    cyan = unreal.LinearColor(0.0, 1.0, 1.0, 1.0)
    yellow = unreal.LinearColor(1.0, 0.8, 0.0, 1.0)
    green = unreal.LinearColor(0.1, 1.0, 0.2, 1.0)
    unreal.SystemLibrary.flush_debug_strings(world)
    if "FrontLedge" in targets:
        goal = unreal.Vector(*targets["FrontLedge"])
        unreal.SystemLibrary.draw_debug_sphere(world, goal, 4.0, 16, yellow, 0.0, 2.0, foreground)
        unreal.SystemLibrary.draw_debug_sphere(world, point, 3.0, 16, cyan, 0.0, 2.0, foreground)
        unreal.SystemLibrary.draw_debug_line(world, point, goal, cyan, 0.0, 2.0, foreground)
        unreal.SystemLibrary.draw_debug_string(world, goal + unreal.Vector(0, 0, 25), "FrontLedge", None, yellow, 0.0)
    if "BackFloor" in targets:
        floor = unreal.Vector(*targets["BackFloor"])
        unreal.SystemLibrary.draw_debug_sphere(world, floor, 5.0, 16, green, 0.0, 2.0, foreground)
        unreal.SystemLibrary.draw_debug_string(world, floor + unreal.Vector(0, 0, 20), "BackFloor", None, green, 0.0)


def start_recording(options):
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    actor = unreal.GameplayStatics.get_player_character(world, 0)
    traversal = next(c for c in actor.get_components_by_class(unreal.ActorComponent) if c.get_class().get_name() == "AC_TraversalLogic_C")
    warp = actor.get_component_by_class(unreal.MotionWarpingComponent)
    name = options.get("case", "trial")
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(exist_ok=True)
    duration = float(options.get("duration", 3.0))
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    dilation = float(options.get("capture_time_dilation", 0.25))
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    half_height = actor.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "motion_warping_disabled": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable"), "capture_time_dilation": dilation, "capsule_half_height": half_height, "start": _vector(actor.get_actor_location()), "setup": STATE.get("case_setup"), "capture_audit": capture_audit({}), "samples": [], "frames": [], "trigger_result": None}
    record["debug_overlay"] = {"yellow": "FrontLedge world target", "cyan": "attach bone world point and line to target", "green": "BackFloor world target", "rendering": "Unreal DrawDebug, foreground depth, does not affect movement"}
    STATE["recording"] = True
    STATE["record"] = record
    STATE["next_capture"] = 0.0
    STATE["triggered"] = False
    STATE["capture_path"] = None
    unreal.GameplayStatics.set_game_paused(world, False)

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            if t >= 0.35 and not STATE["triggered"]:
                inputs = actor.call_method("GetTraversalCheckInputs")
                record["trigger_result"] = str(traversal.call_method("TryTraversalAction", args=(inputs, unreal.DrawDebugTrace.NONE)))
                record["trigger_time"] = t
                STATE["triggered"] = True
            anim = actor.mesh.get_anim_instance()
            montage = anim.get_current_active_montage()
            targets = {}
            for target in warp.get_editor_property("warp_targets"):
                targets[str(target.get_editor_property("name"))] = _vector(target.get_editor_property("location"))
            point = actor.mesh.get_socket_location("attach")
            _draw_measurement_points(world, point, targets)
            record["samples"].append({"t": t, "location": _vector(actor.get_actor_location()), "attach": _vector(point), "montage": montage.get_path_name() if montage else None, "position": anim.montage_get_position(montage) if montage else None, "targets": targets})
            pending = STATE.get("capture_path")
            ready = pending is None or pending.exists()
            if t >= STATE["next_capture"] and t < duration and ready:
                filename = f"frame_{len(record['frames']):04d}.png"
                STATE["capture_path"] = directory / filename
                _capture(STATE["capture_path"])
                record["frames"].append({"file": filename, "t": t})
                STATE["next_capture"] = t + 0.08
            if t >= duration and ready:
                finish()
        except Exception:
            record["error"] = traceback.format_exc()
            finish()

    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory), "duration": duration}


def recording_status(options):
    record = STATE.get("record", {})
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    return {"recording": STATE.get("recording", False), "case": record.get("case"), "frames": len(record.get("frames", [])), "samples": len(record.get("samples", [])), "trigger_result": record.get("trigger_result"), "error": record.get("error"), "last_t": record.get("samples", [{}])[-1].get("t"), "paused": unreal.GameplayStatics.is_game_paused(world) if world else None}


def capture_frame(options):
    name = options.get("name", "capture")
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric image name")
    path = EVIDENCE / (name + ".png")
    _capture(path)
    return {"path": str(path)}


def abort_recording(options):
    if STATE.get("callback"):
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
    STATE["recording"] = False
    return {"recording": False}


def close_message_log(options):
    return {"closed": unreal.get_editor_subsystem(unreal.EditorUtilitySubsystem).close_tab_by_id("MessageLog")}


def restore_session(options):
    if STATE.get("recording"):
        raise RuntimeError("Finish the recording before restoring the session")
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if "original_throttle" in STATE:
        settings.set_editor_property("bThrottleCPUWhenNotForeground", STATE["original_throttle"])
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    unreal.SystemLibrary.execute_console_command(world, "a.MotionWarping.Disable 0")
    unreal.SystemLibrary.execute_console_command(world, "t.MaxFPS 0")
    return {"warp_disabled": 0, "restored_background_throttle": STATE.get("original_throttle")}


def dispatch(action, options):
    actions = {"inventory": inventory, "inspect_asset": inspect_asset, "api_info": api_info, "inspect_actors": inspect_actors, "player_info": player_info, "prepare_case": prepare_case, "configure_view": configure_view, "start_recording": start_recording, "recording_status": recording_status, "capture_frame": capture_frame, "abort_recording": abort_recording, "close_message_log": close_message_log, "restore_session": restore_session, "close_asset_previews": close_asset_previews, "capture_audit": capture_audit}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    result = actions[action](options)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (action + "_latest.json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
