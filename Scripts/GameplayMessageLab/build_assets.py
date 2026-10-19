"""Create the GameplayMessage lab widget and map inside the UnrealEngineLab editor (Docs/UE/GameplayMessage.md).

Run from the editor console: py "<repo>/Scripts/GameplayMessageLab/build_assets.py"
Writes Saved/GameplayMessageLab/build_result.json. Everything it creates lives under /Game/GameplayMessageLab.

  WBP_GMLabFeed           kill feed. Event Construct -> Sequence -> two "Listen for Gameplay Messages" nodes
                            Lab.Message.Elimination (Exact)         -> AddFeedLine
                            Lab.Message.Accolade    (PartialMatch)  -> ShowAccolade (with ActualChannel)
  L_GameplayMessageLab    floor, lights and the camera tagged GMLabCamera. Game mode AGMLabGameMode
"""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Saved/GameplayMessageLab"
UI = "/Game/GameplayMessageLab/UI"
MAP = "/Game/GameplayMessageLab/Maps/L_GameplayMessageLab"
lib = unreal.GMLabEditorLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
result = {}


def check(step, message):
    result.setdefault("steps", []).append({"step": step, "error": message or None})
    if message:
        raise RuntimeError(f"{step}: {message}")


def tag(name):
    value = unreal.GameplayTag()
    value.import_text(f'(TagName="{name}")')
    return value


def build_widget():
    path = f"{UI}/WBP_GMLabFeed"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.get_editor_subsystem(unreal.AssetEditorSubsystem).close_all_editors_for_asset(unreal.load_asset(path))
        unreal.EditorAssetLibrary.delete_asset(path)
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", unreal.GMLabFeedWidget)
    wbp = assets.create_asset("WBP_GMLabFeed", UI, unreal.WidgetBlueprint, factory)
    message = unreal.GMLabCombatMessage.static_struct()
    check("tree", lib.build_feed_widget_tree(wbp))
    check("listen Elimination", lib.add_message_listener_node(wbp, tag("Lab.Message.Elimination"), message, False,
                                                              "AddFeedLine", False, 0))
    check("listen Accolade", lib.add_message_listener_node(wbp, tag("Lab.Message.Accolade"), message, True,
                                                           "ShowAccolade", True, 320))
    check("compile", lib.compile_blueprint(wbp).strip())
    unreal.EditorAssetLibrary.save_loaded_asset(wbp, False)
    result["widget"] = path


def spawn(cls, location, rotation=unreal.Rotator(0, 0, 0), label=None):
    actor = actors.spawn_actor_from_class(cls, location, rotation)
    if label:
        actor.set_actor_label(label)
    return actor


def build_map():
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if unreal.EditorAssetLibrary.does_asset_exist(MAP):
        levels.load_level(MAP)
        for actor in actors.get_all_level_actors():
            if not isinstance(actor, unreal.WorldSettings):
                actors.destroy_actor(actor)
    else:
        levels.new_level(MAP)

    floor = spawn(unreal.StaticMeshActor, unreal.Vector(400, 0, 0), label="Floor")
    floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Plane.Plane"))
    floor.static_mesh_component.set_material(0, unreal.load_asset("/Engine/EngineMaterials/DefaultMaterial.DefaultMaterial"))
    floor.set_actor_scale3d(unreal.Vector(40, 40, 1))

    sun = spawn(unreal.DirectionalLight, unreal.Vector(0, 0, 500), unreal.Rotator(roll=0, pitch=-50, yaw=-30), "Sun")
    sun.light_component.set_editor_property("intensity", 6.0)
    sun.light_component.set_editor_property("atmosphere_sun_light", True)
    spawn(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), label="SkyAtmosphere")
    sky = spawn(unreal.SkyLight, unreal.Vector(0, 0, 300), label="SkyLight")
    sky.light_component.set_editor_property("real_time_capture", True)
    sky.light_component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
    spawn(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), label="Fog")

    # High behind the turrets with a narrow lens, turned 7 degrees to the right so the field fills the left of
    # the screen and the feed widget and the counters fit on the right.
    camera = spawn(unreal.CameraActor, unreal.Vector(-1000, 0, 1827), unreal.Rotator(roll=0, pitch=-50.0, yaw=7.0), "GMLabCamera")
    camera.tags = [unreal.Name("GMLabCamera")]
    camera.camera_component.set_editor_property("field_of_view", 45.0)
    camera.camera_component.set_editor_property("constrain_aspect_ratio", False)

    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", unreal.GMLabGameMode)
    levels.save_current_level()
    result["map"] = MAP


try:
    build_widget()
    build_map()
    result["ok"] = True
except Exception:
    result["error"] = traceback.format_exc()

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "build_result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
unreal.log("GM_LAB: assets built")
