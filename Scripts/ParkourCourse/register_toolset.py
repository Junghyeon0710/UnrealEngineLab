"""Register the Parkour course lab toolset in an editor that already runs an MCP server.

Run from the editor console: py "<repo>/Scripts/ParkourCourse/register_toolset.py"
Only the named actions in pk_lab_runtime.dispatch are reachable. The only asset it saves is the course map
(/Game/ParkourCourse/Maps/L_ParkourCourse).
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
class ParkourLabToolset(unreal.ToolsetDefinition):
    """Build and test the parkour time attack course.

    Actions are restricted to the lab runtime's named operations.
    No source-code or shell-command arguments are accepted.
    """

    @toolset_registry.tool_call
    @staticmethod
    def run_action(action: str, options_json: str = "{}") -> str:
        import pk_lab_runtime
        importlib.reload(pk_lab_runtime)
        return json.dumps(pk_lab_runtime.dispatch(action, json.loads(options_json)))


if not getattr(unreal, "_parkour_lab_registration", None):
    # Keep a reference on the unreal module so the registration outlives this script.
    unreal._parkour_lab_registration = Registration([ParkourLabToolset])
    unreal._parkour_lab_registration.register()
unreal.log("PARKOUR_LAB: toolset registered")
