"""Named Unreal MCP operations for the Motion Warping article.

This module runs inside the interactive GameAnimationSample editor and is reached
only through register_toolset.py -> MotionWarpingLabToolset.run_action.
Everything it spawns lives in the disposable PIE world. Nothing is saved.
"""
from pathlib import Path
import json
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/MotionWarpingLab"
STATE = getattr(unreal, "_motion_warping_lab_state", {})
unreal._motion_warping_lab_state = STATE

CMC_CHARACTER = "/Game/Blueprints/SandboxCharacter_CMC.SandboxCharacter_CMC_C"
TRAVERSABLE_BLOCK = "/Game/Levels/LevelPrototyping/LevelBlock_Traversable.LevelBlock_Traversable_C"
# Empty floor in DefaultLevel, away from the sample's own traversal course.
LAB_FRONT_X = 2500.0
LAB_CENTER_Y = -6500.0
FEET_BONES = ("ball_l", "ball_r", "foot_l", "foot_r")


def _editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _game_world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE first")
    return world


def _vector(vector):
    return [vector.x, vector.y, vector.z]


def _spawn(world, cls, transform):
    # BeginDeferredActorSpawnFromClass has no Python glue; call the reflected UFunction.
    library = unreal.get_default_object(unreal.GameplayStatics)
    scale_method = unreal.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT
    actor = library.call_method("BeginDeferredActorSpawnFromClass", args=(world, cls, transform, unreal.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN, None, scale_method))
    library.call_method("FinishSpawningActor", args=(actor, transform, scale_method))
    return actor


def inventory(options):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    folder = options.get("folder", "/Game/Characters/UEFN_Mannequin/Animations/Traversal")
    assets = registry.get_assets_by_path(folder, recursive=True)
    return {"project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
            "world": _editor_world().get_path_name(),
            "assets": [{"path": str(a.package_name), "class": str(a.asset_class_path.asset_name)} for a in assets]}


def inspect_asset(options):
    asset = unreal.load_asset(options["asset"])
    if not asset:
        raise RuntimeError("Asset not found")
    result = {"path": asset.get_path_name(), "class": asset.get_class().get_name()}
    if isinstance(asset, unreal.AnimMontage):
        result["play_length"] = asset.get_play_length()
        result["windows"] = []
        for window in unreal.MotionWarpingUtilities.get_motion_warping_windows_from_animation(asset):
            state = window.get_editor_property("anim_notify")
            entry = {"start": window.get_editor_property("start_time"), "end": window.get_editor_property("end_time"),
                     "notify_path": state.get_path_name() if state else None}
            modifier = state.get_editor_property("root_motion_modifier") if state else None
            if modifier:
                entry["modifier"] = modifier.get_class().get_name()
                entry["modifier_path"] = modifier.get_path_name()
                for key in ["warp_target_name", "warp_translation", "ignore_z_axis", "warp_to_feet_location", "warp_rotation",
                            "rotation_type", "rotation_method", "warp_point_anim_provider", "warp_point_anim_bone_name"]:
                    try:
                        entry[key] = str(modifier.get_editor_property(key))
                    except Exception:
                        pass
            result["windows"].append(entry)
    return result


def api_info(options):
    cls = getattr(unreal, options["class"])
    return {"class": options["class"], "members": [m for m in dir(cls) if not m.startswith("_")],
            "docs": {m: str(getattr(cls, m).__doc__) for m in options.get("methods", [])}}


def inspect_actors(options):
    world = _game_world() if options.get("pie") else _editor_world()
    result = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if options.get("filter", "").lower() not in (actor.get_name() + actor.get_class().get_name()).lower():
            continue
        center, extent = actor.get_actor_bounds(True)
        result.append({"path": actor.get_path_name(), "class": actor.get_class().get_name(),
                       "bounds_center": _vector(center), "bounds_extent": _vector(extent)})
    return {"world": world.get_path_name(), "actors": result}


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


def prepare_mantle(options):
    """Spawn a test block and a CMC character in PIE, set the CVar, and frame a side camera."""
    world = _game_world()
    height = float(options["height"])
    depth = float(options.get("depth", 200.0))
    width = float(options.get("width", 300.0))
    gap = float(options.get("gap", 110.0))
    yaw = float(options.get("yaw", 0.0))
    disabled = int(bool(options.get("disabled", False)))

    # LevelBlock pivot is its minimum corner; 1.0 scale is a 100cm cube. Its construction
    # script builds the Ledge splines that the sample's traversal trace looks for.
    block_transform = unreal.Transform(location=unreal.Vector(LAB_FRONT_X, LAB_CENTER_Y - width / 2, 0.0),
                                       scale=unreal.Vector(depth / 100, width / 100, height / 100))
    block = _spawn(world, unreal.load_class(None, TRAVERSABLE_BLOCK), block_transform)
    # When the block is spawned at runtime its Ledge spline points are placed correctly but the
    # spline length stays at the template's 100cm. The traversal logic clamps the ledge point by
    # that length, which put FrontLedge 20% of the width off to the side. Rebuild the splines.
    for spline in block.get_components_by_class(unreal.SplineComponent):
        spline.update_spline()

    start = unreal.Vector(LAB_FRONT_X - gap, LAB_CENTER_Y + float(options.get("offset_y", 0.0)), 92.0)
    character = _spawn(world, unreal.load_class(None, CMC_CHARACTER), unreal.Transform(location=start, rotation=unreal.Rotator(0, 0, yaw)))
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    old_pawn = controller.get_controlled_pawn()
    controller.possess(character)
    if old_pawn and old_pawn != character:
        old_pawn.set_actor_hidden_in_game(True)
        old_pawn.set_actor_enable_collision(False)

    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.Disable {disabled}")
    # Debug 2 draws the engine's own points: red = original root motion path, green = warped path.
    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.Debug {int(options.get('engine_debug', 0))}")
    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.DrawDebugLifeTime {float(options.get('debug_lifetime', 1.0))}")

    cam = options.get("camera", {})
    camera_location = unreal.Vector(LAB_FRONT_X + cam.get("x", -20.0), LAB_CENTER_Y + cam.get("y", -560.0), cam.get("z", 150.0))
    look_at = unreal.Vector(LAB_FRONT_X + cam.get("look_x", -20.0), LAB_CENTER_Y, cam.get("look_z", 95.0))
    rotation = unreal.MathLibrary.find_look_at_rotation(camera_location, look_at)
    camera = _spawn(world, unreal.CameraActor, unreal.Transform(location=camera_location, rotation=rotation))
    component = camera.get_component_by_class(unreal.CameraComponent)
    component.set_field_of_view(float(cam.get("fov", 50.0)))
    component.set_constraint_aspect_ratio(False)
    controller.set_view_target_with_blend(camera, 0.0)

    label = options.get("label")
    if label:
        # Drawn by the engine's on-screen debug text, the same as Print String in Blueprint.
        unreal.SystemLibrary.print_string(world, label, True, False, unreal.LinearColor(1, 1, 1, 1), 600.0, "mw_lab_label")

    center, extent = block.get_actor_bounds(False)
    STATE["case_setup"] = {"block": block.get_path_name(), "height": height, "depth": depth, "width": width, "gap": gap, "yaw": yaw,
                           "block_center": _vector(center), "block_extent": _vector(extent),
                           "camera_location": _vector(camera_location), "camera_look_at": _vector(look_at), "label": label}
    STATE["character"] = character
    return {"character": character.get_path_name(), "camera": camera.get_path_name(), "start": _vector(character.get_actor_location()),
            "block_bounds": [_vector(center), _vector(extent)],
            "disabled_value": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable")}


def inspect_ledges(options):
    """World-space points of the Ledge splines that the traversal trace reads."""
    world = _game_world()
    result = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        if not actor.get_class().get_name().startswith("LevelBlock_Traversable"):
            continue
        if options.get("filter") and options["filter"] not in actor.get_name():
            continue
        entry = {"actor": actor.get_name(), "location": _vector(actor.get_actor_location()), "scale": _vector(actor.get_actor_scale3d()), "ledges": []}
        for spline in actor.get_components_by_class(unreal.SplineComponent):
            count = spline.get_number_of_spline_points()
            points = [_vector(spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)) for i in range(count)]
            entry["ledges"].append({"name": spline.get_name(), "points": points, "length": spline.get_spline_length(),
                                    "component_scale": _vector(spline.get_world_scale())})
        result.append(entry)
    return {"blocks": result}


def capture_audit(options):
    world = _game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    manager = unreal.GameplayStatics.get_player_camera_manager(world, 0)
    return {"world": world.get_path_name(), "pawn": unreal.GameplayStatics.get_player_pawn(world, 0).get_path_name(),
            "view_target": pc.get_view_target().get_path_name(),
            "camera_location": _vector(manager.get_camera_location()), "camera_fov": manager.get_fov_angle()}


def _capture(path):
    unreal.SystemLibrary.execute_console_command(_game_world(), f'Shot filename="{path.as_posix()}" -nosuffix')


def capture_frame(options):
    name = options.get("name", "capture")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Use an alphanumeric image name")
    path = EVIDENCE / (name + ".png")
    _capture(path)
    return {"path": str(path)}


def start_recording(options):
    """Trigger the sample's own traversal path and record poses plus real viewport frames."""
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    actor = unreal.GameplayStatics.get_player_character(world, 0)
    traversal = next(c for c in actor.get_components_by_class(unreal.ActorComponent) if c.get_class().get_name() == "AC_TraversalLogic_C")
    warp = actor.get_component_by_class(unreal.MotionWarpingComponent)
    movement = actor.get_component_by_class(unreal.CharacterMovementComponent)
    name = options.get("case", "trial")
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    duration = float(options.get("duration", 2.4))
    trigger_at = float(options.get("trigger_at", 0.3))
    interval = float(options.get("interval", 0.05))
    dilation = float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    half_height = actor.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "motion_warping_disabled": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable"),
              "capture_time_dilation": dilation, "capsule_half_height": half_height, "start": _vector(actor.get_actor_location()),
              "setup": STATE.get("case_setup"), "capture_audit": capture_audit({}), "samples": [], "frames": [], "trigger_result": None}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "triggered": False, "capture_path": None})

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            if t >= trigger_at and not STATE["triggered"]:
                inputs = actor.call_method("GetTraversalCheckInputs")
                # Returns (TraversalCheckFailed, MontageSelectionFailed).
                record["trigger_result"] = str(traversal.call_method("TryTraversalAction", args=(inputs, unreal.DrawDebugTrace.NONE)))
                record["trigger_time"] = t
                STATE["triggered"] = True
            anim = actor.mesh.get_anim_instance()
            montage = anim.get_current_active_montage()
            targets = {}
            for target in warp.get_editor_property("warp_targets"):
                targets[str(target.get_editor_property("name"))] = _vector(target.get_editor_property("location"))
            location = actor.get_actor_location()
            record["samples"].append({
                "t": t, "location": _vector(location), "capsule_bottom_z": location.z - half_height,
                "yaw": actor.get_actor_rotation().yaw,
                "attach": _vector(actor.mesh.get_socket_location("attach")),
                "feet": {b: _vector(actor.mesh.get_socket_location(b)) for b in FEET_BONES},
                "movement_mode": str(movement.get_editor_property("movement_mode")),
                "montage": montage.get_path_name() if montage else None,
                "position": anim.montage_get_position(montage) if montage else None, "targets": targets})
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
            "samples": len(record.get("samples", [])), "trigger_result": record.get("trigger_result"), "error": record.get("error"),
            "last_t": record.get("samples", [{}])[-1].get("t") if record.get("samples") else None}


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
    for command in ("a.MotionWarping.Disable 0", "a.MotionWarping.Debug 0", "a.MotionWarping.DrawDebugLifeTime 1", "t.MaxFPS 0"):
        unreal.SystemLibrary.execute_console_command(world, command)
    return {"warp_disabled": 0, "restored_background_throttle": STATE.get("original_throttle")}


# ---------------------------------------------------------------------------
# Combat example. Runs in the UnrealEngineLab project with the template
# mannequin copied to /Game/Characters/Mannequins (see Docs/UE/AnimationBudget.md).
# ---------------------------------------------------------------------------

COMBAT_MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
COMBAT_QUINN = "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"
COMBAT_ABP = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed.ABP_Unarmed_C"
COMBAT_FOLDER = "/Game/MotionWarpingLab"
COMBAT_MONTAGE = COMBAT_FOLDER + "/AM_Attack_MotionWarping"
COMBAT_MAP = COMBAT_FOLDER + "/MotionWarpingCombat"
COMBAT_TARGET = "AttackTarget"


def inspect_anim(options):
    """Length, root motion flag and root bone translation over time of an animation."""
    anim = unreal.load_asset(options["asset"])
    length = anim.get_play_length()
    steps = int(options.get("steps", 10))
    root = []
    for i in range(steps + 1):
        t = length * i / steps
        pose = unreal.AnimationLibrary.get_bone_pose_for_time(anim, "root", t, False)
        root.append({"t": t, "location": _vector(pose.translation), "yaw": pose.rotation.rotator().yaw})
    return {"path": anim.get_path_name(), "class": anim.get_class().get_name(), "length": length,
            "enable_root_motion": anim.get_editor_property("enable_root_motion") if isinstance(anim, unreal.AnimSequence) else None,
            "skeleton": anim.get_skeleton().get_path_name(), "root": root}


def combat_open_map(options):
    """Create (once) and open an empty test map made from the engine's Basic template."""
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError("Stop PIE before opening the map")
    if not unreal.EditorAssetLibrary.does_asset_exist(COMBAT_MAP):
        if not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).new_level_from_template(COMBAT_MAP, "/Engine/Maps/Templates/Template_Default"):
            raise RuntimeError("Could not create the combat test map")
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    elif _editor_world().get_path_name().split(".")[0] != COMBAT_MAP:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(COMBAT_MAP)
    return {"world": _editor_world().get_path_name()}


def combat_build_montage(options):
    """Make a montage from an attack animation and put one MotionWarping window on it."""
    if unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        # Editor asset functions refuse to run in PIE, and create_asset would then ask to overwrite.
        raise RuntimeError("Stop PIE before building the montage")
    anim = unreal.load_asset(options["source"])
    montage = unreal.load_asset(COMBAT_MONTAGE) if unreal.EditorAssetLibrary.does_asset_exist(COMBAT_MONTAGE) else None
    if montage is None:
        factory = unreal.AnimMontageFactory()
        factory.set_editor_property("source_animation", anim)
        factory.set_editor_property("target_skeleton", anim.get_skeleton())
        montage = unreal.AssetToolsHelpers.get_asset_tools().create_asset(COMBAT_MONTAGE.split("/")[-1], COMBAT_FOLDER, unreal.AnimMontage, factory)
    track = "MotionWarping"
    if track in [str(n) for n in unreal.AnimationLibrary.get_animation_notify_track_names(montage)]:
        unreal.AnimationLibrary.remove_animation_notify_track(montage, track)
    unreal.AnimationLibrary.add_animation_notify_track(montage, track)
    start, end = float(options["start"]), float(options["end"])
    state = unreal.AnimationLibrary.add_animation_notify_state_event(montage, track, start, end - start, unreal.AnimNotifyState_MotionWarping)
    modifier = state.get_editor_property("root_motion_modifier")
    modifier.set_editor_property("warp_target_name", COMBAT_TARGET)
    modifier.set_editor_property("warp_translation", True)
    modifier.set_editor_property("ignore_z_axis", True)
    modifier.set_editor_property("warp_rotation", True)
    bone = options.get("bone")
    if bone:
        modifier.set_editor_property("warp_point_anim_provider", unreal.WarpPointAnimProvider.BONE)
        modifier.set_editor_property("warp_point_anim_bone_name", bone)
    else:
        modifier.set_editor_property("warp_point_anim_provider", unreal.WarpPointAnimProvider.NONE)
    unreal.EditorAssetLibrary.save_loaded_asset(montage, False)
    return inspect_asset({"asset": COMBAT_MONTAGE})


def _combat_character(world, mesh_path, location, yaw):
    character = _spawn(world, unreal.Character, unreal.Transform(location=location, rotation=unreal.Rotator(0, 0, yaw)))
    half_height = character.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
    mesh = character.mesh
    mesh.set_skeletal_mesh_asset(unreal.load_asset(mesh_path))
    mesh.set_relative_location_and_rotation(unreal.Vector(0, 0, -half_height), unreal.Rotator(0, 0, -90), False, True)
    # ACharacter caches the mesh offset in PostInitializeComponents and Motion Warping converts root motion
    # with that cached rotation. Changing the mesh after spawn without this sends the warp 90 degrees off.
    character.cache_initial_mesh_offset(unreal.Vector(0, 0, -half_height), unreal.Rotator(0, 0, -90))
    mesh.set_anim_instance_class(unreal.load_class(None, COMBAT_ABP))
    # Keep the facing that root motion / warping produced instead of snapping back to the controller yaw.
    character.set_editor_property("use_controller_rotation_yaw", False)
    return character


def combat_prepare(options):
    """Attacker at the origin facing +X, enemy at `distance` and `angle` degrees off to the side."""
    world = _game_world()
    origin = unreal.Vector(0.0, 0.0, 100.0)
    distance, angle = float(options.get("distance", 250.0)), float(options.get("angle", 0.0))
    attacker = _combat_character(world, COMBAT_MANNY, origin, 0.0)
    # AddComponentByClass is BlueprintInternalUseOnly, so call the reflected UFunction directly.
    attacker.call_method("AddComponentByClass", args=(unreal.MotionWarpingComponent, False, unreal.Transform(), False))
    rad = unreal.MathLibrary.degrees_to_radians(angle)
    enemy_location = unreal.Vector(origin.x + distance * unreal.MathLibrary.cos(rad), origin.y + distance * unreal.MathLibrary.sin(rad), origin.z)
    enemy = _combat_character(world, COMBAT_QUINN, enemy_location, angle + 180.0)
    enemy.spawn_default_controller()

    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    old_pawn = controller.get_controlled_pawn()
    controller.possess(attacker)
    if old_pawn and old_pawn != attacker:
        old_pawn.set_actor_hidden_in_game(True)
        old_pawn.set_actor_enable_collision(False)

    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.Disable {int(bool(options.get('disabled', False)))}")
    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.Debug {int(options.get('engine_debug', 0))}")
    unreal.SystemLibrary.execute_console_command(world, f"a.MotionWarping.DrawDebugLifeTime {float(options.get('debug_lifetime', 1.0))}")

    cam = options.get("camera", {})
    camera_location = unreal.Vector(cam.get("x", 120.0), cam.get("y", -520.0), cam.get("z", 330.0))
    look_at = unreal.Vector(cam.get("look_x", 120.0), cam.get("look_y", 40.0), cam.get("look_z", 60.0))
    camera = _spawn(world, unreal.CameraActor, unreal.Transform(location=camera_location, rotation=unreal.MathLibrary.find_look_at_rotation(camera_location, look_at)))
    component = camera.get_component_by_class(unreal.CameraComponent)
    component.set_field_of_view(float(cam.get("fov", 55.0)))
    component.set_constraint_aspect_ratio(False)
    controller.set_view_target_with_blend(camera, 0.0)

    STATE["combat"] = {"attacker": attacker, "enemy": enemy}
    STATE["case_setup"] = {"distance": distance, "angle": angle, "attacker": _vector(attacker.get_actor_location()),
                           "enemy": _vector(enemy.get_actor_location()), "camera_location": _vector(camera_location),
                           "camera_look_at": _vector(look_at), "reach": float(options.get("reach", 45.0))}
    return {"attacker": attacker.get_path_name(), "enemy": enemy.get_path_name(), "camera": camera.get_path_name(),
            "has_warping": attacker.get_component_by_class(unreal.MotionWarpingComponent) is not None,
            "disabled_value": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable")}


def combat_start(options):
    """Register the warp target in front of the enemy, play the attack, record poses and frames."""
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    attacker, enemy = STATE["combat"]["attacker"], STATE["combat"]["enemy"]
    warp = attacker.get_component_by_class(unreal.MotionWarpingComponent)
    montage = unreal.load_asset(COMBAT_MONTAGE)
    name = options.get("case", "combat")
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    duration, trigger_at = float(options.get("duration", 2.0)), float(options.get("trigger_at", 0.3))
    interval, dilation = float(options.get("interval", 0.05)), float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    reach = STATE["case_setup"]["reach"]
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "motion_warping_disabled": unreal.SystemLibrary.get_console_variable_int_value("a.MotionWarping.Disable"),
              "capture_time_dilation": dilation, "setup": STATE.get("case_setup"), "montage": montage.get_path_name(),
              "samples": [], "frames": [], "target": None}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "triggered": False, "capture_path": None})

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=2), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            anim = attacker.mesh.get_anim_instance()
            if t >= trigger_at and not STATE["triggered"]:
                # The target sits `reach` cm in front of the enemy, on the line from the enemy to the attacker,
                # and faces the enemy. Same idea as AddOrUpdateWarpTargetFromComponent(VectorFromTargetToOwner).
                enemy_location = enemy.get_actor_location()
                to_attacker = attacker.get_actor_location() - enemy_location
                to_attacker.z = 0.0
                direction = to_attacker.normal()
                target_location = enemy_location + direction * reach
                target_rotation = unreal.MathLibrary.find_look_at_rotation(target_location, enemy_location)
                warp.add_or_update_warp_target_from_location_and_rotation(COMBAT_TARGET, target_location, unreal.Rotator(0, 0, target_rotation.yaw))
                record["target"] = {"location": _vector(target_location), "yaw": target_rotation.yaw}
                record["play_length"] = anim.montage_play(montage)
                record["trigger_time"] = t
                STATE["triggered"] = True
            active = anim.get_current_active_montage()
            enemy_location = enemy.get_actor_location()
            record["samples"].append({
                "t": t, "location": _vector(attacker.get_actor_location()), "yaw": attacker.get_actor_rotation().yaw,
                "hand_r": _vector(attacker.mesh.get_socket_location("hand_r")), "hand_l": _vector(attacker.mesh.get_socket_location("hand_l")),
                "enemy": _vector(enemy_location), "montage": active.get_path_name() if active else None,
                "position": anim.montage_get_position(active) if active else None})
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


def dispatch(action, options):
    actions = {"inventory": inventory, "inspect_asset": inspect_asset, "api_info": api_info, "inspect_actors": inspect_actors,
               "close_asset_previews": close_asset_previews, "configure_view": configure_view, "prepare_mantle": prepare_mantle,
               "capture_audit": capture_audit, "capture_frame": capture_frame, "inspect_ledges": inspect_ledges, "start_recording": start_recording,
               "recording_status": recording_status, "abort_recording": abort_recording, "restore_session": restore_session,
               "inspect_anim": inspect_anim, "combat_open_map": combat_open_map, "combat_build_montage": combat_build_montage,
               "combat_prepare": combat_prepare, "combat_start": combat_start}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    result = actions[action](options)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (action + "_latest.json")).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
