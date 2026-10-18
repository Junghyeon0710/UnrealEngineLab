"""Named Unreal MCP operations for the Control Rig article.

Runs inside the GameAnimationSample editor and is reached only through
register_toolset.py -> ControlRigLabToolset.run_action.
Everything it spawns lives in the disposable PIE world. Nothing is saved.
"""
from pathlib import Path
import json
import math
import traceback
import unreal

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/ControlRigLab"
STATE = getattr(unreal, "_control_rig_lab_state", {})
unreal._control_rig_lab_state = STATE

PAWNS = {"mover": "/Game/Blueprints/SandboxCharacter_Mover.SandboxCharacter_Mover_C",
         "cmc": "/Game/Blueprints/SandboxCharacter_CMC.SandboxCharacter_CMC_C"}
FEET = ("foot_l", "foot_r", "ball_l", "ball_r")


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


def find_actors(options):
    """Actors in the editor (or PIE) world whose label, class or static mesh name contains a keyword."""
    world = _game_world() if options.get("pie") else _editor_world()
    keywords = [k.lower() for k in options.get("keywords", [])]
    out = []
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        names = [actor.get_name(), actor.get_class().get_name()]
        try:
            names.append(actor.get_actor_label())
        except Exception:
            pass
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            if mesh:
                names.append(mesh.get_name())
        text = " ".join(names).lower()
        if not keywords or any(k in text for k in keywords):
            origin, extent = actor.get_actor_bounds(False)
            out.append({"names": names[:6], "location": _vector(actor.get_actor_location()),
                        "rotation": [actor.get_actor_rotation().pitch, actor.get_actor_rotation().yaw, actor.get_actor_rotation().roll],
                        "scale": _vector(actor.get_actor_scale3d()), "bounds_origin": _vector(origin), "extent": _vector(extent)})
        if len(out) >= int(options.get("limit", 200)):
            break
    return {"count": len(out), "actors": out}


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


def console(options):
    """Set GASP / animation CVars (PIE world, or the editor world before PIE) and read them back."""
    world = _editor_world() if options.get("editor") else _game_world()
    allowed = ("DDCVar.", "DDCvar.", "a.", "ControlRig.")
    out = {}
    for name, value in options.get("cvars", {}).items():
        if not name.startswith(allowed) or not str(value).replace(".", "").replace("-", "").isalnum():
            raise ValueError("CVar not allowed: " + name)
        unreal.SystemLibrary.execute_console_command(world, f"{name} {value}")
        out[name] = unreal.SystemLibrary.get_console_variable_int_value(name)
    return {"read_back": out}


def _ground(world, location, ignore):
    """Floor height under a point: line trace from 150cm above to 150cm below on the Visibility channel."""
    start = unreal.Vector(location.x, location.y, location.z + 150.0)
    end = unreal.Vector(location.x, location.y, location.z - 150.0)
    hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if not hit:
        return None
    t = hit.to_tuple()
    # HitResult tuple: (blocking_hit, initial_overlap, time, distance, location, impact_point, normal, impact_normal, ...)
    return {"z": t[5].z, "normal": _vector(t[7])}


def _anim_values(anim, names):
    values = {}
    for key in names:
        try:
            value = anim.get_editor_property(key)
        except Exception:
            continue
        if isinstance(value, (int, float, bool, str)) or value is None:
            values[key] = value
        elif isinstance(value, unreal.Object):
            values[key] = value.get_name()
        else:
            values[key] = str(value)
    return values


def prepare_character(options):
    """Spawn a sandbox character at a location, possess it and point a camera at it."""
    world = _game_world()
    location = unreal.Vector(*options["location"])
    yaw = float(options.get("yaw", 0.0))
    controller = unreal.GameplayStatics.get_player_controller(world, 0)
    if options.get("spawn", False):
        character = _spawn(world, unreal.load_class(None, PAWNS[options.get("pawn", "mover")]),
                           unreal.Transform(location=location, rotation=unreal.Rotator(0, 0, yaw)))
        old_pawn = controller.get_controlled_pawn()
        controller.possess(character)
        if old_pawn and old_pawn != character:
            old_pawn.set_actor_hidden_in_game(True)
            old_pawn.set_actor_enable_collision(False)
    else:
        # The pawn the game mode spawned (DDCvar.PawnClass picks CMC or Mover). Mover only simulates on that one.
        character = controller.get_controlled_pawn()
        # GASP's own teleport: TeleportTo, switch Mover to Falling and point OrientationIntent at the new yaw.
        transform = unreal.Transform(location=location, rotation=unreal.Rotator(0, 0, yaw))
        character.call_method("CustomTeleport", kwargs={"transform": transform, "offset": False, "update_initial_transform": False})
        STATE["teleported"] = True
        controller.set_control_rotation(unreal.Rotator(0, 0, yaw))
    try:
        input_state = character.get_editor_property("CharacterInputState")
        for field, value in (("WantsToStrafe", bool(options.get("strafe", False))), ("WantsToWalk", bool(options.get("walk", False))),
                             ("WantsToSprint", False)):
            try:
                input_state.set_editor_property(field, value)
            except Exception:
                pass
        character.set_editor_property("CharacterInputState", input_state)
    except Exception:
        pass
    camera = _spawn(world, unreal.CameraActor, unreal.Transform(location=location))
    component = camera.get_component_by_class(unreal.CameraComponent)
    component.set_constraint_aspect_ratio(False)
    controller.set_view_target_with_blend(camera, 0.0)
    STATE.update({"character": character, "camera": camera, "camera_offset": options.get("camera", {})})
    _follow_camera()
    return {"character": character.get_path_name(), "camera": camera.get_path_name(), "teleported": STATE.get("teleported"),
            "actor_location": _vector(character.get_actor_location()),
            "anim_class": character.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance().get_class().get_path_name()}


def _mesh(character):
    return character.get_component_by_class(unreal.SkeletalMeshComponent)


def _follow_camera():
    """Camera at a fixed offset from the character (or a fixed anchor), looking at a point near it."""
    character, camera, cam = STATE["character"], STATE["camera"], STATE.get("camera_offset", {})
    anchor = unreal.Vector(*cam["fixed"]) if cam.get("fixed") else character.get_actor_location()
    location = unreal.Vector(anchor.x + cam.get("dx", 0.0), anchor.y + cam.get("dy", 400.0), anchor.z + cam.get("dz", 40.0))
    look = unreal.Vector(anchor.x + cam.get("look_dx", 0.0), anchor.y + cam.get("look_dy", 0.0), anchor.z + cam.get("look_dz", -40.0))
    camera.set_actor_location_and_rotation(location, unreal.MathLibrary.find_look_at_rotation(location, look), False, True)
    camera.get_component_by_class(unreal.CameraComponent).set_field_of_view(float(cam.get("fov", 40.0)))


def set_camera(options):
    STATE["camera_offset"] = options
    _follow_camera()
    return {"camera": options}


def sample_feet(options):
    """Foot bone heights above the floor right under each bone."""
    world = _game_world()
    character = STATE["character"]
    mesh = _mesh(character)
    out = {}
    for bone in options.get("bones", FEET):
        location = mesh.get_socket_location(bone)
        ground = _ground(world, location, [character])
        out[bone] = {"location": _vector(location), "ground_z": ground["z"] if ground else None,
                     "gap": location.z - ground["z"] if ground else None, "normal": ground["normal"] if ground else None}
    out["actor"] = _vector(character.get_actor_location())
    out["pelvis"] = _vector(mesh.get_socket_location("pelvis"))
    out["anim"] = _anim_values(mesh.get_anim_instance(), options.get("anim_names", []))
    return out


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
    """Feed a fixed movement-input script every tick, record foot heights and capture frames."""
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
    # cvar_schedule: [[time, name, value]] console variables switched during the run (e.g. foot placement on/off).
    for _, name, value in options.get("cvar_schedule", []):
        if not name.startswith(("a.AnimNode.", "DDCVar.", "DDCvar.", "ControlRig.")) or not str(value).replace(".", "").isdigit():
            raise ValueError("CVar not allowed: " + name)
    segments = options.get("segments", [])
    duration = float(options.get("duration", 4.0))
    interval = float(options.get("interval", 1 / 30))
    dilation = float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    bones = options.get("bones", list(FEET))
    anim_names = options.get("anim_names", [])
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "setup": options.get("setup"), "segments": segments, "capture_time_dilation": dilation, "samples": [], "frames": []}
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
                    # Mover pawns ignore AddMovementInput; feed IA_Move like a held stick instead.
                    move_input({"x": 0.0, "y": float(scale), "control_yaw": yaw})
                    input_yaw = yaw
            for when, name, value in options.get("cvar_schedule", []):
                key = f"{when}:{name}"
                if t >= when and key not in record.setdefault("cvars_applied", {}):
                    unreal.SystemLibrary.execute_console_command(world, f"{name} {value}")
                    record["cvars_applied"][key] = t
            _follow_camera()
            mesh = _mesh(character)
            sample = {"t": t, "input_yaw": input_yaw, "location": _vector(character.get_actor_location()),
                      "velocity": _vector(character.get_velocity()), "pelvis": _vector(mesh.get_socket_location("pelvis")), "feet": {}}
            for bone in bones:
                location = mesh.get_socket_location(bone)
                ground = _ground(world, location, [character])
                sample["feet"][bone] = _vector(location) + [ground["z"] if ground else None]
            sample.update(_anim_values(mesh.get_anim_instance(), anim_names))
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


def probe_anim(options):
    """Read AnimBP variables by exact Blueprint name (debugging)."""
    anim = _mesh(STATE["character"]).get_anim_instance()
    result = {"class": anim.get_class().get_path_name()}
    for name in options.get("names", []):
        try:
            result[name] = str(anim.get_editor_property(name))
        except Exception as error:
            result[name] = "ERR " + str(error)[:120]
    return result


def restore_session(options):
    if STATE.get("recording"):
        raise RuntimeError("Finish the recording before restoring the session")
    settings = unreal.load_object(None, "/Script/UnrealEd.Default__EditorPerformanceSettings")
    if "original_throttle" in STATE:
        settings.set_editor_property("bThrottleCPUWhenNotForeground", STATE["original_throttle"])
    world = _editor_world()
    for command in options.get("reset", []) + ["DDCvar.DrawCharacterDebugShapes 0", "t.MaxFPS 0"]:
        if command.startswith(("DDCVar.", "DDCvar.", "a.", "t.MaxFPS", "ControlRig.")):
            unreal.SystemLibrary.execute_console_command(world, command)
    return {"restored": True}


def inspect_rig(options):
    """Comments, nodes and variables of a Control Rig blueprint's RigVM graphs (read only)."""
    rig = unreal.load_asset(options["path"])
    out = {"path": rig.get_path_name(), "class": rig.get_class().get_name(), "graphs": []}
    try:
        out["variables"] = [{"name": str(v.name), "type": str(v.cpp_type), "default": str(v.default_value)}
                            for v in rig.get_member_variables()]
    except Exception as error:
        out["variables"] = str(error)
    try:
        hierarchy = rig.get_hierarchy()
        out["hierarchy"] = [{"name": str(k.name), "type": str(k.type).split(".")[-1],
                             "parent": str(hierarchy.get_first_parent(k).name)} for k in hierarchy.get_all_keys()]
    except Exception as error:
        out["hierarchy"] = str(error)
    for model in rig.get_all_models():
        graph = {"name": model.get_node_path() if hasattr(model, "get_node_path") else model.get_name(),
                 "outer": model.get_outer().get_name(), "comments": [], "nodes": []}
        for node in model.get_nodes():
            pos = node.get_position()
            item = {"title": node.get_node_title(), "class": node.get_class().get_name(), "pos": [round(pos.x), round(pos.y)]}
            if options.get("pins") and not isinstance(node, unreal.RigVMCommentNode):
                item["pins"] = {}
                for pin in node.get_pins():
                    default = pin.get_default_value()
                    if default and pin.get_direction() != unreal.RigVMPinDirection.OUTPUT:
                        item["pins"][str(pin.get_name())] = default[:120]
            if isinstance(node, unreal.RigVMCommentNode):
                item["text"] = node.get_comment_text()
                size = node.get_size()
                item["size"] = [round(size.x), round(size.y)]
                graph["comments"].append(item)
            else:
                graph["nodes"].append(item)
        graph["comments"].sort(key=lambda c: (c["pos"][1], c["pos"][0]))
        out["graphs"].append(graph)
    return out


def ground_profile(options):
    """Floor height and slope along a line, from long downward traces (PIE world)."""
    world = _game_world()
    out = []
    for x, y in options["points"]:
        start, end = unreal.Vector(x, y, 5000.0), unreal.Vector(x, y, -500.0)
        hit = unreal.SystemLibrary.line_trace_single(world, start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, False, [],
                                                     unreal.DrawDebugTrace.NONE, True)
        if hit:
            t = hit.to_tuple()
            normal = t[7]
            out.append({"x": x, "y": y, "z": t[5].z, "slope_deg": math.degrees(math.acos(max(-1.0, min(1.0, normal.z)))),
                        "actor": t[9].get_name() if len(t) > 9 and t[9] else None})
        else:
            out.append({"x": x, "y": y, "z": None})
    return {"points": out}


def module_search(options):
    """Names in the unreal module containing every keyword (API discovery)."""
    keys = [k.lower() for k in options["keywords"]]
    return {"names": [n for n in dir(unreal) if all(k in n.lower() for k in keys)][:200]}


def _input_subsystem():
    """Enhanced Input subsystem of the PIE player, reached through the reflected SubsystemBlueprintLibrary."""
    world = _game_world()
    pc = unreal.GameplayStatics.get_player_controller(world, 0)
    library = unreal.find_object(None, "/Script/Engine.Default__SubsystemBlueprintLibrary")
    return library.call_method("GetLocalPlayerSubSystemFromPlayerController", args=(pc, unreal.EnhancedInputLocalPlayerSubsystem))


def move_input(options):
    """Inject one frame of the sample's IA_Move action (2D axis in control-rotation space: X = right, Y = forward)."""
    subsystem = _input_subsystem()
    if "control_yaw" in options:
        pc = unreal.GameplayStatics.get_player_controller(_game_world(), 0)
        pc.set_control_rotation(unreal.Rotator(0, 0, float(options["control_yaw"])))
    subsystem.inject_input_vector_for_action(unreal.load_asset("/Game/Input/IA_Move"),
                                             unreal.Vector(float(options["x"]), float(options["y"]), 0.0), [], [])
    return {"x": options["x"], "y": options["y"]}

def open_level(options):
    """Load one of the sample's levels in the editor without saving anything."""
    path = options["path"]
    if not path.startswith("/Game/Levels/"):
        raise ValueError("Only sample levels")
    dirty = [p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty:
        raise RuntimeError("Unsaved map changes, not switching: " + ", ".join(dirty))
    ok = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(path)
    return {"loaded": ok, "world": _editor_world().get_path_name()}


def _plain(value, depth=0):
    """Struct/array/object to plain JSON-able data for inspection."""
    if depth > 6:
        return str(value)
    if isinstance(value, (int, float, bool, str)) or value is None:
        return value
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    if isinstance(value, (list, tuple, unreal.Array)):
        return [_plain(v, depth + 1) for v in value]
    if isinstance(value, unreal.Map):
        return {str(k): _plain(v, depth + 1) for k, v in value.items()}
    if isinstance(value, unreal.StructBase):
        try:
            data = value.to_dict()
        except Exception:
            data = {}
        # Blueprint structs have no Python fields; fall back to their exported text.
        return {k: _plain(v, depth + 1) for k, v in data.items()} if data else value.export_text()
    return str(value)


def dump_object(options):
    """All editor-visible properties of an object as plain data (data assets, CDOs)."""
    obj = unreal.load_object(None, options["path"])
    out = {"path": obj.get_path_name(), "class": obj.get_class().get_name(), "properties": {}}
    for name in options.get("properties", []):
        try:
            out["properties"][name] = _plain(obj.get_editor_property(name))
        except Exception as error:
            out["properties"][name] = "ERR " + str(error)[:120]
    return out


POI_GIZMO = "/Game/IsolatedExamples/LookAtPOI/TestLevelContent/Props/BP_LookAtPOI_TargetGizmo.BP_LookAtPOI_TargetGizmo_C"
POI_BONES = ("pelvis", "spine_05", "head")


def _actor_by_label(world, label):
    for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
        try:
            if actor.get_actor_label() == label:
                return actor
        except Exception:
            continue
    raise RuntimeError("No actor labelled " + label)


def poi_setup(options):
    """Pick one LookAtPOI sample pawn, spawn the sample's target gizmo and a fixed camera."""
    world = _game_world()
    pawn = _actor_by_label(world, options["pawn"])
    anim = pawn.get_component_by_class(unreal.SkeletalMeshComponent).get_anim_instance()
    gizmo = _spawn(world, unreal.load_class(None, POI_GIZMO), unreal.Transform(location=unreal.Vector(*options["target"])))
    if options.get("hide_gizmo"):
        gizmo.set_actor_hidden_in_game(True)          # still the PC's target, just not drawn
    camera = _spawn(world, unreal.CameraActor, unreal.Transform(location=unreal.Vector(*options["camera"]["location"])))
    look = unreal.Vector(*options["camera"]["look_at"])
    location = unreal.Vector(*options["camera"]["location"])
    camera.set_actor_location_and_rotation(location, unreal.MathLibrary.find_look_at_rotation(location, look), False, True)
    component = camera.get_component_by_class(unreal.CameraComponent)
    component.set_constraint_aspect_ratio(False)
    component.set_field_of_view(float(options["camera"].get("fov", 40.0)))
    unreal.GameplayStatics.get_player_controller(world, 0).set_view_target_with_blend(camera, 0.0)
    STATE.update({"poi_pawn": pawn, "poi_anim": anim, "poi_gizmo": gizmo, "camera": camera})
    enabled = bool(options.get("enabled", True))
    if enabled:
        # The sample's own path: PC_LookAtPOI "Zone Selected" turns LookAtPOI on for that pawn and then, every tick,
        # writes the gizmo position into the AnimBP's LookAtPOI Target. Those variables are not editable from Python.
        pc = unreal.GameplayStatics.get_player_controller(world, 0)
        pc.call_method(options.get("select_event", "Zone Was Selected"), args=(pawn, str(options.get("zone_type", "Loops")), gizmo))
    STATE["poi_gizmo_offset"] = unreal.Vector(0.0, 0.0, 0.0)
    _poi_target(unreal.Vector(*options["target"]), enabled)
    if enabled:
        STATE["poi_gizmo_offset"] = unreal.Vector(0.0, 50.0, 0.0)   # measured: target = gizmo + (0, 50, 0)
        _poi_target(unreal.Vector(*options["target"]), enabled)
    return {"pawn": pawn.get_path_name(), "anim": anim.get_class().get_path_name(), "gizmo": gizmo.get_path_name(),
            "pawn_location": _vector(pawn.get_actor_location()), "pawn_yaw": pawn.get_actor_rotation().yaw}


def _poi_target(location, enabled):
    # PC_LookAtPOI aims at a point in front of the gizmo, so move the gizmo by that offset to aim at `location`.
    offset = STATE.get("poi_gizmo_offset", unreal.Vector(0.0, 0.0, 0.0))
    STATE["poi_gizmo"].set_actor_location(location - offset, False, True)


def _bone_axes(mesh, bone):
    transform = mesh.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
    rotation = transform.rotation
    return {"location": _vector(transform.translation),
            "x": _vector(rotation.get_axis_x()), "y": _vector(rotation.get_axis_y()), "z": _vector(rotation.get_axis_z())}


def poi_run(options):
    """Move the target along an arc around the pawn every tick, record bone axes and capture frames."""
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    pawn, anim = STATE["poi_pawn"], STATE["poi_anim"]
    mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
    name = options["case"]
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    center = unreal.Vector(*options["center"])          # arc center (usually the pawn) and target height
    radius = float(options["radius"])
    keys = options["keys"]                              # [[time, angle in degrees from the pawn's facing]]
    facing = pawn.get_actor_rotation().yaw
    enabled = bool(options.get("enabled", True))
    duration = float(options.get("duration", keys[-1][0]))
    interval = float(options.get("interval", 1 / 30))
    dilation = float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "setup": options.get("setup"), "pawn": pawn.get_actor_label(), "facing_yaw": facing, "center": _vector(center),
              "radius": radius, "keys": keys, "enabled": enabled, "capture_time_dilation": dilation, "samples": [], "frames": []}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "capture_path": None})

    def angle_at(t):
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, a0), (t1, a1) in zip(keys, keys[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
                u = u * u * (3 - 2 * u)                  # ease in/out between keys
                return a0 + (a1 - a0) * u
        return keys[-1][1]

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            angle = angle_at(t)
            rad = math.radians(facing + angle)
            target = unreal.Vector(center.x + radius * math.cos(rad), center.y + radius * math.sin(rad), center.z)
            _poi_target(target, enabled)
            sample = {"t": t, "angle": angle, "target": _vector(target), "actor_yaw": pawn.get_actor_rotation().yaw,
                      "anim_target": _vector(anim.get_editor_property("LookAtPOI Target")),
                      "anim_enabled": bool(anim.get_editor_property("LookAtPOI Enabled")),
                      "bones": {b: _bone_axes(mesh, b) for b in POI_BONES}}
            for curve in ("face__l_eye_h", "face__r_eye_h"):
                try:
                    sample[curve] = anim.get_curve_value(curve)
                except Exception:
                    pass
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

    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory), "duration": duration}


def poi_probe(options):
    """Read LookAtPOI variables back from the anim instance and the pawn (debugging)."""
    out = {}
    if options.get("set_target"):
        for label, obj in (("anim", STATE["poi_anim"]), ("pawn", STATE["poi_pawn"])):
            for name, value in (("LookAtPOI Target", unreal.Vector(*options["set_target"])), ("LookAtPOI Enabled", True)):
                try:
                    obj.set_editor_property(name, value)
                    out[f"set {label}.{name}"] = "ok"
                except Exception as error:
                    out[f"set {label}.{name}"] = "ERR " + str(error)[:160]
    for label, obj in (("anim", STATE["poi_anim"]), ("pawn", STATE["poi_pawn"])):
        for name in options.get("names", ["LookAtPOI Target", "LookAtPOI Enabled", "LookAtPOI Dev Mode", "ABP Mode", "LookAtPOI DA Asset"]):
            try:
                out[f"{label}.{name}"] = str(obj.get_editor_property(name))
            except Exception as error:
                out[f"{label}.{name}"] = "ERR " + str(error)[:100]
    return out


def poi_walker(options):
    """Put the PIE player character (CMC) at a spot around the LookAtPOI pawn, facing along the walk."""
    world = _game_world()
    walker = unreal.GameplayStatics.get_player_pawn(world, 0)
    location = unreal.Vector(*options["location"])
    walker.set_actor_location_and_rotation(location, unreal.Rotator(0, 0, float(options.get("yaw", 0.0))), False, True)
    try:
        state = walker.get_editor_property("CharacterInputState")
        state.set_editor_property("WantsToStrafe", False)
        state.set_editor_property("WantsToWalk", bool(options.get("walk", True)))
        walker.set_editor_property("CharacterInputState", state)
    except Exception:
        pass
    STATE["poi_walker"] = walker
    return {"walker": walker.get_path_name(), "location": _vector(walker.get_actor_location())}


def poi_walk_run(options):
    """The player character walks an arc around the pawn; the pawn's LookAtPOI target is the walker's head."""
    if STATE.get("recording"):
        raise RuntimeError("A recording is already running")
    world = _game_world()
    pawn, anim, walker = STATE["poi_pawn"], STATE["poi_anim"], STATE["poi_walker"]
    mesh = pawn.get_component_by_class(unreal.SkeletalMeshComponent)
    walker_mesh = walker.get_component_by_class(unreal.SkeletalMeshComponent)
    name = options["case"]
    if not name.replace("_", "").isalnum():
        raise ValueError("Use an alphanumeric case name")
    directory = EVIDENCE / name
    directory.mkdir(parents=True, exist_ok=True)
    center = pawn.get_actor_location()
    facing = pawn.get_actor_rotation().yaw
    radius = float(options["radius"])
    end_angle = float(options["end_angle"])         # degrees from the pawn's facing, where the walk stops
    direction = 1.0 if float(options.get("direction", 1.0)) > 0 else -1.0
    lead = float(options.get("lead", 20.0))
    scale = float(options.get("input_scale", 1.0))
    start_delay = float(options.get("start_delay", 0.3))
    duration = float(options["duration"])
    interval = float(options.get("interval", 1 / 30))
    dilation = float(options.get("capture_time_dilation", 0.2))
    capture = bool(options.get("capture", True))
    start_time = unreal.GameplayStatics.get_time_seconds(world)
    unreal.GameplayStatics.set_global_time_dilation(world, dilation)
    record = {"case": name, "project": unreal.Paths.get_project_file_path(), "engine": unreal.SystemLibrary.get_engine_version(),
              "setup": options.get("setup"), "pawn": pawn.get_actor_label(), "facing_yaw": facing, "center": _vector(center),
              "radius": radius, "end_angle": end_angle, "capture_time_dilation": dilation, "samples": [], "frames": []}
    STATE.update({"recording": True, "record": record, "next_capture": 0.0, "capture_path": None})

    def relative_angle(point):
        a = math.degrees(math.atan2(point.y - center.y, point.x - center.x)) - facing
        return (a + 180.0) % 360.0 - 180.0

    def finish():
        unreal.unregister_slate_post_tick_callback(STATE.pop("callback"))
        STATE["recording"] = False
        unreal.GameplayStatics.set_global_time_dilation(world, 1.0)
        (directory / "measurements.json").write_text(json.dumps(record, indent=1), encoding="utf-8")

    def tick(delta):
        try:
            t = unreal.GameplayStatics.get_time_seconds(world) - start_time
            here = walker.get_actor_location()
            angle = relative_angle(here)
            walking = t >= start_delay and (end_angle - angle) * direction > 0
            if walking:
                # Steer toward a point a little further along the circle, so the walk stays on the arc.
                aim = math.radians(facing + angle + direction * lead)
                goal = unreal.Vector(center.x + radius * math.cos(aim), center.y + radius * math.sin(aim), here.z)
                move = goal - here
                move.z = 0.0
                walker.add_movement_input(move.normal(), scale, False)
            head = walker_mesh.get_socket_location("head")
            _poi_target(head, True)
            sample = {"t": t, "walking": walking, "walker": _vector(here), "walker_angle": angle, "head": _vector(head),
                      "anim_target": _vector(anim.get_editor_property("LookAtPOI Target")),
                      "anim_enabled": bool(anim.get_editor_property("LookAtPOI Enabled")),
                      "bones": {b: _bone_axes(mesh, b) for b in POI_BONES}}
            for curve in ("face__l_eye_h", "face__r_eye_h"):
                try:
                    sample[curve] = anim.get_curve_value(curve)
                except Exception:
                    pass
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

    STATE["callback"] = unreal.register_slate_post_tick_callback(tick)
    return {"case": name, "directory": str(directory), "duration": duration}


def dispatch(action, options):
    actions = {"api_info": api_info, "inspect_object": inspect_object, "find_actors": find_actors,
               "close_asset_previews": close_asset_previews, "configure_view": configure_view, "console": console,
               "prepare_character": prepare_character, "set_camera": set_camera, "sample_feet": sample_feet,
               "capture_audit": capture_audit, "capture_frame": capture_frame, "start_run": start_run,
               "recording_status": recording_status, "abort_recording": abort_recording, "probe_anim": probe_anim,
               "restore_session": restore_session, "inspect_rig": inspect_rig, "ground_profile": ground_profile, "module_search": module_search, "move_input": move_input, "open_level": open_level, "dump_object": dump_object, "poi_setup": poi_setup, "poi_run": poi_run, "poi_probe": poi_probe, "poi_walker": poi_walker, "poi_walk_run": poi_walk_run}
    if action not in actions:
        raise ValueError("Unknown lab action: " + action)
    result = actions[action](options)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / (action + "_latest.json")).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result
