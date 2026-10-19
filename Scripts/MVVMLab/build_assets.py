"""Create the MVVM lab widgets and map inside the UnrealEngineLab editor (Docs/UE/MVVM.md).

Run from the editor console: py "<repo>/Scripts/MVVMLab/build_assets.py"
Writes Saved/MVVMLab/build_result.json. Everything it creates lives under /Game/MVVMLab.

  WBP_StatusMVVM     ViewModel from the Global Viewmodel Collection, five bindings, one event
  WBP_StatusMini     the same ViewModel, two bindings
  WBP_StatusClassic  UMG property bindings to functions of UMVVMLabClassicStatusWidget
  L_MVVMLab          empty map whose game mode is AMVVMLabGameMode
"""
from pathlib import Path
import json
import traceback
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Saved/MVVMLab"
UI = "/Game/MVVMLab/UI"
MAP = "/Game/MVVMLab/Maps/L_MVVMLab"
VM = "Status"                 # name in the widget's Viewmodels panel
GLOBAL_NAME = "PlayerStatus"  # AMVVMLabGameMode::StatusViewModelName
lib = unreal.MVVMLabEditorLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()
result = {}


def check(step, message):
    result.setdefault("steps", []).append({"step": step, "error": message or None})
    if message:
        raise RuntimeError(f"{step}: {message}")


def new_widget(name, parent):
    path = f"{UI}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", parent)
    return assets.create_asset(name, UI, unreal.WidgetBlueprint, factory)


def finish(widget):
    check(widget.get_name() + " compile", lib.compile_widget_blueprint(widget).strip())
    unreal.EditorAssetLibrary.save_loaded_asset(widget, False)


def main():
    # 1. MVVM view: Viewmodels panel + View Bindings panel
    wbp = new_widget("WBP_StatusMVVM", unreal.UserWidget)
    check("tree", lib.build_status_widget_tree(wbp, "MVVM  View A", False))
    check("viewmodel", lib.add_global_view_model(wbp, unreal.MVVMLabStatusViewModel.static_class(), VM, GLOBAL_NAME))
    for source, widget, prop in [("GetHealthPercent", "HealthBar", "Percent"), ("GetHealthText", "HealthText", "Text"),
                                 ("GetAmmoText", "AmmoText", "Text")]:
        check(f"binding {widget}.{prop}", lib.add_view_model_binding(wbp, VM, source, widget, prop))
    check("binding LowHealthText.Visibility", lib.add_view_model_visibility_binding(wbp, VM, "IsLowHealth", "LowHealthText"))
    check("event HealButton.OnClicked", lib.add_view_model_event(wbp, "HealButton", "OnClicked", VM, "RequestHeal"))
    finish(wbp)

    # 2. A second view on the same ViewModel
    mini = new_widget("WBP_StatusMini", unreal.UserWidget)
    check("mini tree", lib.build_status_widget_tree(mini, "MVVM  View B  (same ViewModel)", True))
    check("mini viewmodel", lib.add_global_view_model(mini, unreal.MVVMLabStatusViewModel.static_class(), VM, GLOBAL_NAME))
    check("mini binding HealthBar", lib.add_view_model_binding(mini, VM, "GetHealthPercent", "HealthBar", "Percent"))
    check("mini binding HealthText", lib.add_view_model_binding(mini, VM, "GetHealthText", "HealthText", "Text"))
    finish(mini)

    # 3. The same panel with classic UMG property bindings
    classic = new_widget("WBP_StatusClassic", unreal.MVVMLabClassicStatusWidget)
    check("classic tree", lib.build_status_widget_tree(classic, "Classic  UMG Property Binding", False))
    for widget, prop, function in [("HealthBar", "Percent", "GetHealthPercentBinding"), ("HealthText", "Text", "GetHealthTextBinding"),
                                   ("AmmoText", "Text", "GetAmmoTextBinding"), ("LowHealthText", "Visibility", "GetLowHealthVisibilityBinding")]:
        check(f"classic {widget}.{prop}", lib.add_classic_function_binding(classic, widget, prop, function))
    finish(classic)

    # 4. Map
    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        levels.new_level(MAP)
    else:
        levels.load_level(MAP)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property("default_game_mode", unreal.MVVMLabGameMode)
    levels.save_current_level()
    result["map"] = MAP
    result["ok"] = True


try:
    main()
except Exception:
    result["error"] = traceback.format_exc()

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "build_result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
unreal.log("MVVM_LAB: assets built")
