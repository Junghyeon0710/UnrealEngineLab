"""Register the Control Rig lab toolset in an editor that already runs an MCP server.

Run from the editor console: py "<repo>/Scripts/ControlRig/register_toolset.py"
Only the named actions in cr_lab_runtime.dispatch are reachable. Nothing is saved.
"""
from pathlib import Path
import importlib
import json
import sys
import unreal
import toolset_registry
from toolset_registry.registration import Registration

SCRIPT_DIR = str(Path(__file__).resolve().parent)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


@unreal.uclass()
class ControlRigLabToolset(unreal.ToolsetDefinition):
    """Run fixed Control Rig experiments in GameAnimationSample.

    Actions are restricted to the lab runtime's named operations.
    No source-code or shell-command arguments are accepted.
    """

    @toolset_registry.tool_call
    @staticmethod
    def run_action(action: str, options_json: str = "{}") -> str:
        import cr_lab_runtime
        importlib.reload(cr_lab_runtime)
        return json.dumps(cr_lab_runtime.dispatch(action, json.loads(options_json)))


if not getattr(unreal, "_control_rig_lab_registration", None):
    # Keep a reference on the unreal module so the registration outlives this script.
    unreal._control_rig_lab_registration = Registration([ControlRigLabToolset])
    unreal._control_rig_lab_registration.register()
unreal.log("CONTROL_RIG_LAB: toolset registered")
