"""Play L_MVVMLab in PIE through Unreal MCP and record what the article measures (Docs/UE/MVVM.md).

1. measure      no capture. 0-10 s nothing changes, 10 s the demo starts, 18 s a heal through the ViewModel.
2. burst_auto   no capture. After the demo, three heals in the same tick (Auto execution mode).
3. demo_click   'Shot showui' frames every 0.2 s. The demo, then the real HEAL button of View A is clicked.

The editor must run the MCP server, have register_toolset.py executed once and L_MVVMLab open.
"""
import re
import time

from mcp_client import Client, EDITOR, SLATE, lab, value, restore_editor_window


def fresh_pie(client):
    restore_editor_window("UnrealEngineLab")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
        time.sleep(1.5)
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 2.0}}))
    time.sleep(3.0)
    lab(client, "configure_view", {"fps": 30})
    assert lab(client, "pie_status")["game_mode"] == "MVVMLabGameMode"


def wait_recording(client, timeout=300):
    deadline = time.monotonic() + timeout
    while True:
        status = lab(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            lab(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(1.0)


def heal_button(client):
    """The first 'HEAL +25' button in the editor window is the one of WBP_StatusMVVM (View A)."""
    tree = value(client.call(SLATE, "Snapshot", {"ref": "", "maxDepth": 400}))
    return re.findall(r'button "HEAL \+25".*\[ref=(\w+)\]', tree)[0]


if __name__ == "__main__":
    client = Client()

    fresh_pie(client)
    lab(client, "record", {"case": "measure", "duration": 20.0, "capture": False,
                           "actions": [[0.0, "reset_counters"], [10.0, "start_demo", [0.6]],
                                       [18.0, "request_heal_through_view_model"]]})
    print("measure", wait_recording(client))

    fresh_pie(client)
    lab(client, "record", {"case": "burst_auto", "duration": 10.5, "capture": False,
                           "actions": [[0.0, "start_demo", [0.6]], [8.5, "reset_counters"]]
                           + [[9.5, "request_heal_through_view_model"]] * 3})
    print("burst_auto", wait_recording(client))

    fresh_pie(client)
    button = heal_button(client)
    started = time.monotonic()
    lab(client, "record", {"case": "demo_click", "duration": 14.0, "interval": 0.2, "capture": True,
                           "actions": [[0.0, "reset_counters"], [2.0, "start_demo", [0.6]]]})
    while time.monotonic() - started < 11.3:
        time.sleep(0.05)
    value(client.call(SLATE, "Click", {"ref": button}))
    print("demo_click", wait_recording(client))

    value(client.call(EDITOR, "StopPIE"))
    lab(client, "restore_session")
    print("Trials completed.")
