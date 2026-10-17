"""Run four real PIE trials via Unreal MCP. Sample assets are never saved.

First open GameAnimationSample with the lab startup script and MCP port 8001.
The editor must remain interactive, not a -ExecutePythonScript batch session.
"""
from pathlib import Path
import json
import time
import argparse
from datetime import datetime

from mcp_client import sample_client, lab, value

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "Saved/MotionWarpingLab"
CASES = [
    ("depth50_on", False, [2300.0, -2400.0, 90.0]), ("depth50_off", True, [2300.0, -2400.0, 90.0]),
    ("depth20_on", False, [2330.0, -2600.0, 90.0]), ("depth20_off", True, [2330.0, -2600.0, 90.0]),
]


def wait_recording(client):
    deadline = time.monotonic() + 80
    while True:
        status = lab(client, "recording_status")
        if not status["recording"]:
            if status.get("error"):
                raise RuntimeError(status["error"])
            return status
        if time.monotonic() > deadline:
            lab(client, "abort_recording")
            raise TimeoutError(status)
        time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reuse", action="store_true", help="Reuse completed recordings instead of running fresh trials")
    parser.add_argument("--case", action="append", choices=[c[0] for c in CASES], help="Run only the named cases")
    args = parser.parse_args()
    client = sample_client()
    wait_recording(client)
    assets = value(client.call("EditorToolset.EditorAppToolset", "GetOpenAssets"))
    lab(client, "close_asset_previews", {"assets": assets})
    assert not value(client.call("EditorToolset.EditorAppToolset", "GetOpenAssets")), "Close asset preview viewports before Shot captures"
    for name, disabled, start in CASES:
        if args.case and name not in args.case:
            continue
        output = EVIDENCE / name / "measurements.json"
        if args.reuse and output.exists() and not json.loads(output.read_text()).get("error"):
            print(name, "existing complete recording", flush=True)
            continue
        folder = EVIDENCE / name
        if folder.exists():
            archive = EVIDENCE / (name + "_archive_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))
            # Verify both absolute paths before moving a generated capture directory.
            assert folder.resolve().is_relative_to(EVIDENCE.resolve())
            assert archive.resolve().is_relative_to(EVIDENCE.resolve())
            folder.rename(archive)
        if value(client.call("EditorToolset.EditorAppToolset", "IsPIERunning")):
            value(client.call("EditorToolset.EditorAppToolset", "StopPIE"))
        value(client.call("EditorToolset.EditorAppToolset", "StartPIE", {"options": {
            "bSimulate": False, "playMode": "PlayMode_InViewPort", "warmupSeconds": 1.0
        }}))
        lab(client, "configure_view")
        config = lab(client, "prepare_case", {"disabled": disabled, "start": start})
        assert config["disabled_value"] == int(disabled)
        audit = lab(client, "capture_audit")
        assert "UEDPIE_" in audit["world"] and "CameraActor_" in audit["view_target"], audit
        lab(client, "start_recording", {"case": name, "duration": 2.0, "capture_time_dilation": 0.25})
        print(name, wait_recording(client), flush=True)
    montages = {}
    for name, _, _ in CASES:
        record = json.loads((EVIDENCE / name / "measurements.json").read_text())
        for sample in record["samples"]:
            asset = sample["montage"]
            if asset and asset not in montages:
                montages[asset] = lab(client, "inspect_asset", {"asset": asset})
    (EVIDENCE / "montages.json").write_text(json.dumps(montages, indent=2), encoding="utf-8")
    if value(client.call("EditorToolset.EditorAppToolset", "IsPIERunning")):
        value(client.call("EditorToolset.EditorAppToolset", "StopPIE"))
    lab(client, "restore_session")
    print("Requested PIE trials completed.", flush=True)
