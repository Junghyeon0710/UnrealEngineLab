"""Named Unreal MCP operations for the parkour time attack course.

Runs inside an editor (GameAnimationSample for asset checks and migration, UnrealEngineLab for
building and testing the course) and is reached only through register_toolset.py ->
ParkourLabToolset.run_action.
"""
from pathlib import Path
import json
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/ParkourCourseLab"
STATE = getattr(unreal, "_parkour_lab_state", {})
unreal._parkour_lab_state = STATE


def _registry():
    return unreal.AssetRegistryHelpers.get_asset_registry()


def _package_files(package):
    """Files on disk that make up a /Game package (uasset/umap plus bulk data)."""
    relative = package[len("/Game/"):]
    content = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()))
    base = content / relative
    return [p for p in base.parent.glob(base.name + ".*") if p.suffix in (".uasset", ".umap", ".ubulk", ".uexp", ".uptnl")]


def dependency_report(options):
    """Every /Game package the roots need (hard and soft references), with sizes on disk."""
    registry = _registry()
    dep_options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=bool(options.get("soft", True)),
                                                         include_hard_package_references=True,
                                                         include_searchable_names=False,
                                                         include_soft_management_references=False,
                                                         include_hard_management_references=False)
    pending = list(options["roots"])
    seen = set()
    script_modules = set()
    while pending:
        package = pending.pop()
        if package in seen or not package.startswith("/Game/"):
            continue
        seen.add(package)
        for dep in registry.get_dependencies(package, dep_options) or []:
            dep = str(dep)
            if dep.startswith("/Script/"):
                script_modules.add(dep)
            elif dep.startswith("/Game/") and dep not in seen:
                pending.append(dep)
    packages = []
    for package in sorted(seen):
        files = _package_files(package)
        packages.append({"package": package, "bytes": sum(f.stat().st_size for f in files),
                         "largest_file": max((f.stat().st_size for f in files), default=0)})
    folders = {}
    for item in packages:
        key = "/".join(item["package"].split("/")[:5])
        folders[key] = folders.get(key, 0) + item["bytes"]
    return {"roots": options["roots"], "package_count": len(packages), "total_bytes": sum(p["bytes"] for p in packages),
            "largest": sorted(packages, key=lambda p: -p["largest_file"])[:15],
            "folders": dict(sorted(folders.items(), key=lambda kv: -kv[1])[:40]),
            "packages": [p["package"] for p in packages] if options.get("list") else None,
            "script_modules": sorted(script_modules)}


def inspect_object(options):
    """Read named editor properties of any loaded object (assets, CDOs)."""
    obj = unreal.load_object(None, options["path"])
    if not obj:
        raise RuntimeError("Object not found")
    result = {"path": obj.get_path_name(), "class": obj.get_class().get_name()}
    for prop in options.get("properties", []):
        try:
            value = obj.get_editor_property(prop)
            result[prop] = value.get_path_name() if isinstance(value, unreal.Object) else str(value)
        except Exception as error:
            result[prop] = {"error": str(error)}
    return result


def referencers_of_scripts(options):
    """Which of the given /Game packages depend on each listed /Script module."""
    registry = _registry()
    dep_options = unreal.AssetRegistryDependencyOptions(include_soft_package_references=False, include_hard_package_references=True,
                                                         include_searchable_names=False, include_soft_management_references=False,
                                                         include_hard_management_references=False)
    wanted = set(options["modules"])
    out = {m: [] for m in wanted}
    for package in options["packages"]:
        for dep in registry.get_dependencies(package, dep_options) or []:
            dep = str(dep)
            if dep in wanted:
                out[dep].append(package)
    return out


def dirty_packages(options):
    """Unsaved map and content packages in this editor (checked before closing or switching levels)."""
    return {"maps": [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
            "content": [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}


def load_check(options):
    """Load assets and report class, Blueprint compile status and parent class (after importing the sample assets)."""
    out = []
    for path in options["paths"]:
        entry = {"path": path}
        try:
            asset = unreal.load_asset(path)
            entry["class"] = asset.get_class().get_name() if asset else None
            if isinstance(asset, unreal.Blueprint):
                entry["status"] = str(asset.get_editor_property("status"))
                generated = asset.generated_class()
                entry["generated"] = generated.get_name() if generated else None
        except Exception as error:
            entry["error"] = str(error)[:300]
        out.append(entry)
    return {"assets": out}


COURSE_TAG = "ParkourCourse"


def _editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def _vector(v):
    return [v.x, v.y, v.z]


def open_course_map(options):
    """Open the course map, creating an empty one the first time."""
    path = options["path"]
    if not path.startswith("/Game/ParkourCourse/"):
        raise ValueError("Course maps live under /Game/ParkourCourse/")
    if _editor_world().get_path_name().split(".")[0] == path:
        return {"world": _editor_world().get_path_name(), "created": False, "already_open": True}
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError("Unsaved map changes, not switching: " + ", ".join(dirty))
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    created = False
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        levels.load_level(path)
    else:
        created = levels.new_level(path)
    return {"world": _editor_world().get_path_name(), "created": created}


def _course_actors():
    return [a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if COURSE_TAG in [str(t) for t in a.tags]]


def clear_course(options):
    """Remove everything this script placed (actors tagged ParkourCourse)."""
    actors = _course_actors()
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).destroy_actors(actors)
    return {"removed": len(actors)}


def place_actor(options):
    """Place one actor in the editor level with transform, label and editable properties."""
    cls = unreal.load_class(None, options["class"])
    if not cls:
        raise RuntimeError("Class not found: " + options["class"])
    location = unreal.Vector(*options.get("location", [0, 0, 0]))
    rotation = unreal.Rotator(*options.get("rotation", [0, 0, 0]))  # roll, pitch, yaw
    actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(cls, location, rotation)
    actor.set_actor_scale3d(unreal.Vector(*options.get("scale", [1, 1, 1])))
    actor.set_actor_label(options.get("label", actor.get_name()))
    tags = list(actor.tags)
    tags.append(unreal.Name(COURSE_TAG))
    actor.tags = tags
    for name, value in options.get("properties", {}).items():
        if isinstance(value, list) and len(value) == 3:
            value = unreal.Vector(*value)
        elif isinstance(value, dict) and "enum" in value:
            value = getattr(getattr(unreal, value["enum"]), value["value"])
        actor.set_editor_property(name, value)
    if options.get("folder"):
        actor.set_folder_path(options["folder"])
    # LevelBlock_Traversable sets its ledge spline points in the construction script but, when spawned from a script,
    # the cached spline length stays at the template's 100 cm and traversal targets land off-centre. Rebuild it.
    splines = actor.get_components_by_class(unreal.SplineComponent)
    for spline in splines:
        spline.update_spline()
    origin, extent = actor.get_actor_bounds(False)
    return {"actor": actor.get_name(), "label": actor.get_actor_label(), "location": _vector(actor.get_actor_location()),
            "bounds_origin": _vector(origin), "bounds_extent": _vector(extent),
            "spline_lengths": [round(sp.get_spline_length(), 1) for sp in splines]}


def set_game_mode(options):
    settings = _editor_world().get_world_settings()
    cls = unreal.load_class(None, options["class"])
    settings.set_editor_property("default_game_mode", cls)
    if "kill_z" in options:
        settings.set_editor_property("kill_z", float(options["kill_z"]))
    return {"game_mode": cls.get_path_name()}


def save_course_map(options):
    world = _editor_world()
    if not world.get_path_name().startswith("/Game/ParkourCourse/"):
        raise RuntimeError("Not the course map: " + world.get_path_name())
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    return {"saved": ok, "world": world.get_path_name()}


def course_report(options):
    out = []
    for actor in _course_actors():
        origin, extent = actor.get_actor_bounds(False)
        out.append({"label": actor.get_actor_label(), "class": actor.get_class().get_name(),
                    "location": _vector(actor.get_actor_location()), "rotation": [actor.get_actor_rotation().roll,
                    actor.get_actor_rotation().pitch, actor.get_actor_rotation().yaw], "scale": _vector(actor.get_actor_scale3d()),
                    "bounds_origin": _vector(origin), "bounds_extent": _vector(extent)})
    return {"actors": out}


def ground_profile(options):
    """Walkable height and slope under points, from long downward traces (editor or PIE world)."""
    import math
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() if options.get("pie") else _editor_world()
    out = []
    for x, y in options["points"]:
        hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 5000.0), unreal.Vector(x, y, -2000.0),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                     unreal.DrawDebugTrace.NONE, True)
        if hit:
            t = hit.to_tuple()
            out.append({"x": x, "y": y, "z": round(t[5].z, 1), "slope": round(math.degrees(math.acos(max(-1.0, min(1.0, t[7].z)))), 1),
                        "actor": t[9].get_actor_label() if len(t) > 9 and t[9] else None})
        else:
            out.append({"x": x, "y": y, "z": None})
    return {"points": out}


def _game_world():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
    if not world:
        raise RuntimeError("Start PIE first")
    return world


def pie_status(options):
    """Game mode, pawn and run state in PIE."""
    world = _game_world()
    mode = unreal.GameplayStatics.get_game_mode(world)
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    pawn = pc.get_controlled_pawn() if pc else None
    out = {"world": world.get_path_name(), "game_mode": mode.get_class().get_name() if mode else None,
           "controller": pc.get_class().get_name() if pc else None,
           "pawn": pawn.get_class().get_name() if pawn else None,
           "pawn_location": _vector(pawn.get_actor_location()) if pawn else None,
           "hud": pc.get_hud().get_class().get_name() if pc and pc.get_hud() else None}
    if mode and hasattr(mode, "get_run_state"):
        reached, total = mode.get_progress()
        out.update({"run_state": str(mode.get_run_state()), "elapsed": mode.get_elapsed_seconds(), "best": mode.get_best_seconds(),
                    "progress": [reached, total], "falls": mode.get_fall_count()})
    return out


def capture_frame(options):
    name = options.get("name", "capture")
    if not name.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Use an alphanumeric image name")
    path = EVIDENCE / (name + ".png")
    path.parent.mkdir(parents=True, exist_ok=True)
    unreal.SystemLibrary.execute_console_command(_game_world(), f'Shot filename="{path.as_posix()}" -nosuffix')
    return {"path": str(path)}


def _input_subsystem(world):
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    library = unreal.find_object(None, "/Script/Engine.Default__SubsystemBlueprintLibrary")
    return pc, library.call_method("GetLocalPlayerSubSystemFromPlayerController", args=(pc, unreal.EnhancedInputLocalPlayerSubsystem))


ANIM_VARIABLES = ("CurrentSelectedDatabase", "CurrentSelectedAnim", "MM Search Cost", "MovementMode", "MovementState", "Gait",
                  "Speed2D", "FootPlacement_Enable")
FEET = ("ball_l", "ball_r")


def _short(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, unreal.Object):
        return value.get_name()
    return str(value).split(".")[-1].split(":")[0]


def _anim_values(anim):
    out = {}
    for name in ANIM_VARIABLES:
        try:
            out[name] = _short(anim.get_editor_property(name))
        except Exception:
            pass
    try:
        out["ValidDatabases"] = [_short(db) for db in anim.get_editor_property("ValidDatabases")]
    except Exception:
        pass
    return out


def _foot_heights(world, pawn):
    """Height of each ball bone above the floor right under it (trace ignores the pawn)."""
    mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
    out = {}
    for bone in FEET:
        location = mesh.get_socket_location(bone)
        hit = unreal.SystemLibrary.line_trace_single(world, location + unreal.Vector(0, 0, 150), location - unreal.Vector(0, 0, 150),
                                                     unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [pawn],
                                                     unreal.DrawDebugTrace.NONE, True)
        out[bone] = round(location.z - hit.to_tuple()[5].z, 2) if hit else None
    out["pelvis_above_capsule"] = round(mesh.get_socket_location("pelvis").z - pawn.get_actor_location().z, 2)
    return out


def _warp_targets(pawn):
    component = pawn.get_component_by_class(unreal.MotionWarpingComponent)
    if not component:
        return None
    out = []
    for target in component.get_editor_property("warp_targets"):
        try:
            transform = target.get_editor_property("location"), target.get_editor_property("rotation")
            out.append({"name": str(target.get_editor_property("name")), "location": _vector(transform[0]),
                        "yaw": transform[1].yaw})
        except Exception as error:
            out.append({"error": str(error)[:120]})
    return out


def console(options):
    """Set animation / debug CVars in the PIE world (or the editor world) and read them back."""
    world = _editor_world() if options.get("editor") else _game_world()
    out = {}
    for name, value in options.get("cvars", {}).items():
        allowed = name.startswith(("a.", "DDCvar.", "DDCVar.", "ControlRig.")) or name == "r.MotionBlurQuality"
        if not allowed or not str(value).replace(".", "").isdigit():
            raise ValueError("CVar not allowed: " + name)
        unreal.SystemLibrary.execute_console_command(world, f"{name} {value}")
        out[name] = unreal.SystemLibrary.get_console_variable_int_value(name)
    return {"read_back": out}


def _side_camera(pawn, side):
    """Film the pawn from the side with its own (unused) CameraComponent instead of the sample's gameplay camera."""
    components = pawn.get_components_by_class(unreal.SceneComponent)
    camera = next(c for c in components if c.get_class().get_name() == "CameraComponent")
    if not camera.is_active():
        for component in components:
            if component.get_class().get_name() == "GameplayCameraComponent":
                component.deactivate()
        camera.activate(True)
        camera.set_absolute(True, True, True)
        camera.set_field_of_view(float(side.get("fov", 50)))
    here = pawn.get_actor_location()
    ox, oy, oz = side.get("offset", [0, -400, 0])
    camera.set_world_location_and_rotation(unreal.Vector(here.x + ox, here.y + oy, here.z + oz),
                                           unreal.Rotator(roll=0.0, pitch=float(side.get("pitch", 0)), yaw=float(side.get("yaw", 90))),
                                           False, False)


def autoplay(options):
    """Play the course with the sample's own input actions: hold IA_Move forward, tap IA_Jump at given X positions.

    Records the pawn and the game mode every tick and captures the player's view (with the HUD) at an interval.
    """
    import math
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    name = options["case"]
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    move = unreal.load_asset("/Game/Input/IA_Move")
    jump = unreal.load_asset("/Game/Input/IA_Jump")
    sprint = unreal.load_asset("/Game/Input/IA_Sprint")
    jumps = sorted(float(x) for x in options.get("jump_at_x", []))
    jump_frames = int(options.get("jump_frames", 3))
    duration = float(options.get("duration", 30.0))
    stop_after_finish = float(options.get("stop_after_finish", 1.5))
    interval = float(options.get("interval", 1 / 30))
    dilation = float(options.get("capture_time_dilation", 1.0))
    capture = bool(options.get("capture", False))
    yaw = float(options.get("yaw", 0.0))
    steer_y = options.get("steer_y")            # keep to this Y line by steering the input
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "options": options, "engine": unreal.SystemLibrary.get_engine_version(), "samples": [], "frames": [],
              "jumps": []}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "capture_path": None, "jump_left": 0,
                  "next_jump": 0, "finished_at": None})

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            pc, inputs = _input_subsystem(world)
            pawn = pc.get_controlled_pawn()
            mode = unreal.GameplayStatics.get_game_mode(world)
            if pawn and STATE["finished_at"] is None:
                here = pawn.get_actor_location()
                direction = yaw
                target_y = steer_y
                for plan_x, plan_y in options.get("steer_plan", []):   # [[x, y]]: from x on, steer toward y
                    if here.x >= plan_x:
                        target_y = plan_y
                if target_y is not None:
                    direction = yaw + max(-60.0, min(60.0, (float(target_y) - here.y) * 0.3))
                pc.set_control_rotation(unreal.Rotator(0.0, -10.0, direction))
                inputs.inject_input_vector_for_action(move, unreal.Vector(0.0, 1.0, 0.0), [], [])
                if options.get("sprint"):
                    inputs.inject_input_vector_for_action(sprint, unreal.Vector(1.0, 0.0, 0.0), [], [])
                index = STATE["next_jump"]
                if index < len(jumps) and here.x >= jumps[index]:
                    STATE["jump_left"] = jump_frames
                    STATE["next_jump"] = index + 1
                    record["jumps"].append({"t": t, "x": here.x})
                if STATE["jump_left"] > 0:
                    inputs.inject_input_vector_for_action(jump, unreal.Vector(1.0, 0.0, 0.0), [], [])
                    STATE["jump_left"] -= 1
                side = options.get("side_camera")    # {"from_x", "offset", "pitch", "yaw", "fov"}
                if side and here.x >= float(side.get("from_x", -1e9)):
                    _side_camera(pawn, side)
            reached, total = mode.get_progress()
            montage = None
            if pawn:
                anim = pawn.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
                active = anim.get_current_active_montage() if anim else None
                montage = active.get_name() if active else None
            extra = {}
            if pawn and options.get("detail"):
                anim = pawn.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
                extra = {"anim": _anim_values(anim), "feet": _foot_heights(world, pawn)}
                if montage:
                    extra["warp_targets"] = _warp_targets(pawn)
            sample = {"t": t, "montage": montage, **extra, "location": _vector(pawn.get_actor_location()) if pawn else None,
                      "velocity": _vector(pawn.get_velocity()) if pawn else None,
                      "state": str(mode.get_run_state()).split(".")[-1].split(":")[0], "elapsed": mode.get_elapsed_seconds(),
                      "progress": reached, "falls": mode.get_fall_count()}
            record["samples"].append(sample)
            if sample["state"] == "FINISHED" and STATE["finished_at"] is None:
                STATE["finished_at"] = t
            pending = STATE.get("capture_path")
            ready = pending is None or pending.exists()
            windows = options.get("capture_windows")
            in_window = not windows or any(w0 <= t <= w1 for w0, w1 in windows)
            if capture and in_window and t >= STATE["next_capture"] and ready:
                filename = f"frame_{len(record['frames']):04d}.png"
                STATE["capture_path"] = directory / filename
                # showui: debug text drawn with DrawDebugString lives on the debug canvas, which a plain Shot leaves out.
                # It captures the whole editor window, so the exporter crops the viewport back out.
                ui = " showui" if options.get("capture_ui") else ""
                unreal.SystemLibrary.execute_console_command(world, f'Shot{ui} filename="{STATE["capture_path"].as_posix()}" -nosuffix')
                record["frames"].append({"file": filename, "t": t})
                STATE["next_capture"] = t + interval
            done = t >= duration or (STATE["finished_at"] is not None and t >= STATE["finished_at"] + stop_after_finish)
            if done and ready:
                finish()
        except Exception:
            record["error"] = traceback.format_exc()
            finish()

    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory)}


def recording_status(options):
    record = STATE.get("record", {})
    last = record["samples"][-1] if record.get("samples") else None
    return {"recording": STATE.get("recording", False), "case": record.get("case"), "frames": len(record.get("frames", [])),
            "samples": len(record.get("samples", [])), "error": record.get("error"), "last": last}


def abort_recording(options):
    if STATE.get("callback"):
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
    STATE["recording"] = False
    return {"recording": False}


def configure_view(options):
    """Keep PIE ticking at a steady rate while recording (editor in the background, capped FPS)."""
    world = _game_world()
    for command in ("t.MaxFPS 30",):
        unreal.SystemLibrary.execute_console_command(world, command)
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    STATE.setdefault("original_throttle", settings.get_editor_property("bThrottleCPUWhenNotForeground"))
    settings.set_editor_property("bThrottleCPUWhenNotForeground", False)
    return {"throttle_off": True}


def restore_session(options):
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if "original_throttle" in STATE:
        settings.set_editor_property("bThrottleCPUWhenNotForeground", STATE["original_throttle"])
    unreal.SystemLibrary.execute_console_command(_editor_world(), "t.MaxFPS 0")
    return {"restored": True}


def frame_rate(options):
    """Measure ticks per second of PIE for a short window (returns immediately, read with frame_rate_result)."""
    world = _game_world()
    STATE["fps"] = {"start": unreal.GameplayStatics.get_real_time_seconds(world), "ticks": 0, "game0": unreal.GameplayStatics.get_time_seconds(world)}

    def tick(delta):
        STATE["fps"]["ticks"] += 1
        if STATE["fps"]["ticks"] >= int(options.get("ticks", 60)):
            unreal.unregister_slate_post_tick_callback(STATE.pop("fps_callback"))
            STATE["fps"]["real"] = unreal.GameplayStatics.get_real_time_seconds(world) - STATE["fps"]["start"]
            STATE["fps"]["game"] = unreal.GameplayStatics.get_time_seconds(world) - STATE["fps"]["game0"]

    STATE["fps_callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"measuring": True}


def frame_rate_result(options):
    return STATE.get("fps", {})


def input_mappings(options):
    """Keys bound to each Input Action in an Input Mapping Context."""
    imc = unreal.load_asset(options["path"])
    try:
        mappings = imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
    except Exception:
        mappings = imc.get_editor_property("mappings")
    out = {}
    for mapping in mappings:
        action = mapping.get_editor_property("action")
        key = mapping.get_editor_property("key")
        out.setdefault(action.get_name() if action else "None", []).append(str(key.get_editor_property("key_name")))
    return out


def dispatch(action, options):
    actions = {"dependency_report": dependency_report, "inspect_object": inspect_object,
               "referencers_of_scripts": referencers_of_scripts, "dirty_packages": dirty_packages, "load_check": load_check,
               "open_course_map": open_course_map, "clear_course": clear_course, "place_actor": place_actor,
               "set_game_mode": set_game_mode, "save_course_map": save_course_map, "course_report": course_report, "ground_profile": ground_profile, "pie_status": pie_status, "capture_frame": capture_frame,
               "autoplay": autoplay, "recording_status": recording_status, "abort_recording": abort_recording,
               "configure_view": configure_view, "restore_session": restore_session, "frame_rate": frame_rate,
               "frame_rate_result": frame_rate_result, "input_mappings": input_mappings, "console": console}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    try:
        result = actions[action](options)
    except Exception:
        raise RuntimeError(traceback.format_exc())
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (action + "_latest.json")).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result
