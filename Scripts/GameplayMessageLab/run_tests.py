"""Play L_GameplayMessageLab in PIE through Unreal MCP and record what the article measures (Docs/UE/GameplayMessage.md).

1. demo        'Shot showui' frames every 0.15 s. The turrets shoot one round (a shot every 0.6 s) with
               GameplayMessageSubsystem.LogMessages on, so every broadcast is also in the output log.
2. order       four listeners on Lab.Message.Test / Lab.Message, frame numbers before, inside and after the broadcast
3. mismatch    FGMLabOtherMessage broadcast on Lab.Message.Elimination
4. benchmark   GameplayMessage vs a multicast delegate, 3 runs each for 1, 10 and 100 listeners

Writes Saved/GameplayMessageLab/<case>/measurements.json and Saved/GameplayMessageLab/tests.json.
The editor must run the MCP server, have register_toolset.py executed once and L_GameplayMessageLab open.
"""
from pathlib import Path
import json
import time

from mcp_client import Client, EDITOR, lab, value, restore_editor_window

OUT = Path(__file__).resolve().parents[2] / "Saved/GameplayMessageLab"


def checked(client, action, options=None):
    result = lab(client, action, options)
    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(result["error"])
    return result


def fresh_pie(client):
    restore_editor_window("UnrealEngineLab")
    if value(client.call(EDITOR, "IsPIERunning")):
        value(client.call(EDITOR, "StopPIE"))
        time.sleep(1.5)
    value(client.call(EDITOR, "StartPIE", {"options": {"bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 2.0}}))
    time.sleep(3.0)
    checked(client, "configure_view", {"fps": 30})
    assert checked(client, "pie_status")["game_mode"] == "GMLabGameMode"


def wait_recording(client, timeout=300):
    deadline = time.monotonic() + timeout
    while True:
        status = checked(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            checked(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(1.0)


def call(client, function, *args):
    return checked(client, "call", {"function": function, "args": list(args)})


if __name__ == "__main__":
    client = Client()
    tests = {}

    fresh_pie(client)
    checked(client, "console", {"command": "GameplayMessageSubsystem.LogMessages 1"})
    checked(client, "record", {"case": "demo", "duration": 10.5, "interval": 0.15, "capture": True,
                               "actions": [[0.0, "reset_counters"], [0.8, "start_demo", [0.6]]]})
    print("demo", wait_recording(client))
    tests["demo_counters"] = checked(client, "pie_status")["counters"]

    tests["order"] = call(client, "run_order_test")["returned"]
    tests["mismatch"] = call(client, "run_mismatch_test")["returned"]
    checked(client, "console", {"command": "GameplayMessageSubsystem.LogMessages 0"})

    tests["benchmark"] = []
    for broadcasts, listeners in [(100000, 1), (100000, 10), (10000, 100)]:
        runs = [call(client, "run_benchmark", broadcasts, listeners)["returned"] for _ in range(3)]
        tests["benchmark"].append(runs)
        print("benchmark", listeners, [(r["message_us"], r["delegate_us"]) for r in runs])

    (OUT / "tests.json").write_text(json.dumps(tests, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in tests.items() if k != "benchmark"}, indent=1))
    print("Trials completed. PIE is still running for the editor captures.")
