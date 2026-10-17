"""Register transient lab tools and inspect GameAnimationSample without saving assets."""
from pathlib import Path
import json
import importlib
import sys
import unreal
import toolset_registry
from toolset_registry.registration import Registration

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


@unreal.uclass()
class MotionWarpingLabToolset(unreal.ToolsetDefinition):
    """Inspect and run fixed Motion Warping experiments in GameAnimationSample.

    Actions are restricted to the local lab runtime's named operations.
    No source-code or shell-command arguments are accepted.
    """

    @toolset_registry.tool_call
    @staticmethod
    def run_action(action: str, options_json: str = "{}") -> str:
        import mw_lab_runtime
        importlib.reload(mw_lab_runtime)
        return json.dumps(mw_lab_runtime.dispatch(action, json.loads(options_json)))


_lab_registration = Registration([MotionWarpingLabToolset])
_lab_registration.register()
unreal.SystemLibrary.execute_console_command(None, "ModelContextProtocol.StartServer 8001")

EVIDENCE = Path(__file__).resolve().parents[2] / "Saved/MotionWarpingLab"
EVIDENCE.mkdir(parents=True, exist_ok=True)
registry = unreal.AssetRegistryHelpers.get_asset_registry()
assets = registry.get_assets_by_path("/Game/Characters/UEFN_Mannequin/Animations/Traversal", recursive=True)
report = {
    "project": unreal.Paths.get_project_file_path(),
    "engine": unreal.SystemLibrary.get_engine_version(),
    "world": unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name(),
    "traversal_assets": [{"path": str(a.package_name), "class": str(a.asset_class_path.asset_name)} for a in assets],
    "motion_warping_methods": [x for x in dir(unreal.MotionWarpingComponent) if not x.startswith("_")],
}
(EVIDENCE / "sample_inventory.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
unreal.log("MOTION_WARPING_LAB: read-only inventory completed")
