"""Turn the recorded PIE frames into the article's GIFs/stills and write the measurements.

Only real `Shot` frames are used. Processing is limited to cropping, resizing,
placing OFF/ON side by side, and a one-line label. No pose or geometry is drawn.
"""
from pathlib import Path
import argparse
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/MotionWarpingLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/MotionWarping"
HEIGHTS = (60, 100, 150)
CROP = (330, 50, 1030, 860)          # region of the 1358x870 PIE viewport that holds the action
PANEL = (430, 498)                   # each side after resizing
GAP = 6
STANDING_OFFSET = 2.3                # capsule bottom above the floor while walking on flat ground
FONT = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 17)


def load(height, mode):
    record = json.loads((SOURCE / f"mantle_h{height}_{mode}" / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    assert record["motion_warping_disabled"] == (1 if mode == "off" else 0)
    assert record["trigger_result"] == "(False, False)", record["trigger_result"]
    assert "UEDPIE_" in record["capture_audit"]["world"] and "CameraActor_" in record["capture_audit"]["view_target"]
    assert record["setup"]["height"] == height
    return record


def frame_at(record, mode, height, t_after_trigger, prefix="mantle"):
    frame = min(record["frames"], key=lambda f: abs(f["t"] - record["trigger_time"] - t_after_trigger))
    image = Image.open(SOURCE / f"{prefix}_h{height}_{mode}" / frame["file"]).convert("RGB").crop(CROP)
    return image.resize(PANEL, Image.Resampling.LANCZOS), frame


def label(image, text):
    draw = ImageDraw.Draw(image)
    draw.text((12, 10), text, font=FONT, fill="white", stroke_width=3, stroke_fill="black")
    return image


def pair(left, right):
    canvas = Image.new("RGB", (left.width * 2 + GAP, left.height), "black")
    canvas.paste(left, (0, 0))
    canvas.paste(right, (left.width + GAP, 0))
    return canvas


def save_gif(frames, durations, path):
    palette_source = Image.new("RGB", (frames[0].width, frames[0].height * 4))
    for i, index in enumerate(range(0, len(frames), max(1, len(frames) // 4))):
        if i < 4:
            palette_source.paste(frames[index], (0, frames[0].height * i))
    palette = palette_source.quantize(colors=144, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)


def comparison_gif(height, records, speed=0.5, step=0.05):
    """OFF | ON clips aligned by time since TryTraversalAction. Played at `speed`."""
    frames, durations = [], []
    times = [round(-0.15 + i * step, 3) for i in range(int(2.3 / step) + 1)]
    for t in times:
        off, _ = frame_at(records["off"], "off", height, t)
        on, _ = frame_at(records["on"], "on", height, t)
        frames.append(pair(label(off, "Motion Warping OFF"), label(on, "Motion Warping ON")))
        durations.append(round(step / speed * 1000))
    durations[-1] = 1200
    path = OUT / f"motionwarping-mantle-{height}cm.gif"
    save_gif(frames, durations, path)
    return path


def montage_window_ends(montage):
    data = json.loads((SOURCE / "montages.json").read_text())[montage]
    return [w["end"] for w in data["windows"] if w.get("warp_target_name") == "FrontLedge"]


def measure(record):
    active = [s for s in record["samples"] if s["position"] is not None]
    montages = sorted({s["montage"] for s in active})
    assert len(montages) == 1, montages
    top = record["setup"]["height"]
    window_end = max(montage_window_ends(montages[0]))
    at_end = min(active, key=lambda s: abs(s["position"] - window_end))
    target = at_end["targets"]["FrontLedge"]
    # After the last FrontLedge window the mantle holds its height until blend out.
    hold = [s for s in active if s["position"] > window_end + 0.1]
    hold_bottom = sum(s["capsule_bottom_z"] for s in hold) / len(hold)
    after = [s for s in record["samples"] if s["t"] > hold[-1]["t"]]
    jump = max((abs(b["capsule_bottom_z"] - a["capsule_bottom_z"]), b["t"]) for a, b in zip([hold[-1]] + after, after))
    return {"montage": montages[0], "block_top_cm": top, "frontledge_window_end_s": window_end,
            "sample_position_s": at_end["position"], "attach": at_end["attach"], "frontledge_target": target,
            "attach_error_cm": math.dist(at_end["attach"], target),
            "hold_capsule_bottom_cm": hold_bottom, "hold_gap_to_top_cm": hold_bottom - STANDING_OFFSET - top,
            "final_capsule_bottom_cm": record["samples"][-1]["capsule_bottom_z"],
            "largest_step_after_montage_cm": jump[0], "largest_step_time_s": jump[1]}


def grid(records_by_height, mode, t):
    """The same moment of the montage for all three heights, one fixed camera."""
    tiles = []
    for height in HEIGHTS:
        image, _ = frame_at(records_by_height[height][mode], mode, height, t)
        tiles.append(label(image, f"{height}cm  {mode.upper()}"))
    canvas = Image.new("RGB", (PANEL[0] * 3 + GAP * 2, PANEL[1]), "black")
    for i, tile in enumerate(tiles):
        canvas.paste(tile, (i * (PANEL[0] + GAP), 0))
    return canvas


def export_mantle():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "montages.json").write_bytes((SOURCE / "montages.json").read_bytes())
    records = {h: {m: load(h, m) for m in ("off", "on")} for h in HEIGHTS}
    summary = {}
    for height in HEIGHTS:
        pair_records = records[height]
        off_m, on_m = measure(pair_records["off"]), measure(pair_records["on"])
        assert off_m["montage"] == on_m["montage"], (off_m["montage"], on_m["montage"])
        summary[f"{height}cm"] = {"off": off_m, "on": on_m}
        path = comparison_gif(height, pair_records)
        print(path.name, path.stat().st_size // 1024, "KB")
    # Stills: the hold phase after the last FrontLedge window, the same moment for every height.
    for mode in ("off", "on"):
        grid({h: records[h] for h in HEIGHTS}, mode, 1.15).save(OUT / f"motionwarping-mantle-heights-{mode}.png", optimize=True)
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    # The engine's own Motion Warping debug points (red: original root motion, blue: actor feet).
    debug = []
    for height in (60, 150):
        record = json.loads((SOURCE / f"debug_h{height}_on" / "measurements.json").read_text())
        image, _ = frame_at(record, "on", height, 1.6, prefix="debug")
        debug.append(label(image, f"{height}cm  ON  a.MotionWarping.Debug 2"))
    pair(*debug).save(OUT / "motionwarping-mantle-engine-debug.png", optimize=True)
    for height, pair_summary in summary.items():
        for mode, m in pair_summary.items():
            print(f"{height:>6} {mode:<3} hold gap {m['hold_gap_to_top_cm']:+6.1f}cm  attach err {m['attach_error_cm']:5.1f}cm"
                  f"  final {m['final_capsule_bottom_cm']:6.1f}  step {m['largest_step_after_montage_cm']:5.1f}cm")


# ---------------------------------------------------------------------------
# Combat example (UnrealEngineLab project)
# ---------------------------------------------------------------------------

COMBAT_CROP = (240, 0, 1060, 800)
COMBAT_PANEL = (430, 420)
COMBAT_IMPACT = 0.4667  # left hook of MM_Attack_02
COMBAT_CASES = {"far": ("260cm, 35°", 260, 35), "side": ("140cm, 60°", 140, 60)}


def combat_load(case, mode):
    record = json.loads((SOURCE / f"combat_{case}_{mode}" / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    assert record["motion_warping_disabled"] == (1 if mode == "off" else 0)
    assert record["setup"]["distance"] == COMBAT_CASES[case][1] and record["setup"]["angle"] == COMBAT_CASES[case][2]
    return record


def combat_frame(record, case, mode, t_after_trigger):
    frame = min(record["frames"], key=lambda f: abs(f["t"] - record["trigger_time"] - t_after_trigger))
    image = Image.open(SOURCE / f"combat_{case}_{mode}" / frame["file"]).convert("RGB").crop(COMBAT_CROP)
    return image.resize(COMBAT_PANEL, Image.Resampling.LANCZOS)


def combat_at(record, position):
    """Linear interpolation of the recorded samples at a montage position."""
    active = [s for s in record["samples"] if s["position"] is not None]
    before = max((s for s in active if s["position"] <= position), key=lambda s: s["position"])
    after = min((s for s in active if s["position"] >= position), key=lambda s: s["position"])
    a = 0.0 if after["position"] == before["position"] else (position - before["position"]) / (after["position"] - before["position"])
    mix = lambda x, y: [p + (q - p) * a for p, q in zip(x, y)]
    return {"location": mix(before["location"], after["location"]), "hand_l": mix(before["hand_l"], after["hand_l"]),
            "yaw": before["yaw"] + (after["yaw"] - before["yaw"]) * a, "enemy": before["enemy"],
            "sample_positions": [before["position"], after["position"]]}


def combat_measure(record):
    hit = combat_at(record, COMBAT_IMPACT)
    enemy, target = hit["enemy"], record["target"]
    to_enemy = math.degrees(math.atan2(enemy[1] - hit["location"][1], enemy[0] - hit["location"][0]))
    return {"montage": record["montage"], "impact_position_s": COMBAT_IMPACT, "interpolated_from": hit["sample_positions"],
            "enemy": enemy, "target": target, "root_at_impact": hit["location"], "yaw_at_impact": hit["yaw"],
            "yaw_to_enemy": to_enemy, "facing_error_deg": abs(to_enemy - hit["yaw"]),
            "fist_to_enemy_centre_cm": math.dist(hit["hand_l"][:2], enemy[:2]),
            "root_to_target_cm": math.dist(hit["location"][:2], target["location"][:2]),
            "final_location": record["samples"][-1]["location"], "final_yaw": record["samples"][-1]["yaw"]}


def export_combat():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "combat_montage.json").write_bytes((SOURCE / "combat_montage.json").read_bytes())
    summary, impact_rows = {}, []
    for case, (text, _, _) in COMBAT_CASES.items():
        records = {mode: combat_load(case, mode) for mode in ("off", "on")}
        summary[case] = {mode: combat_measure(records[mode]) for mode in ("off", "on")}
        frames, durations, step, speed = [], [], 0.05, 0.5
        for i in range(int(1.35 / step) + 1):
            t = round(-0.15 + i * step, 3)
            frames.append(pair(label(combat_frame(records["off"], case, "off", t), "Motion Warping OFF"),
                               label(combat_frame(records["on"], case, "on", t), "Motion Warping ON")))
            durations.append(round(step / speed * 1000))
        durations[-1] = 1200
        path = OUT / f"motionwarping-combat-{case}.gif"
        save_gif(frames, durations, path)
        print(path.name, path.stat().st_size // 1024, "KB")
        # The still is the hit frame: trigger time + impact position (montage starts at the trigger).
        impact_rows.append(pair(label(combat_frame(records["off"], case, "off", COMBAT_IMPACT), f"{text}  OFF"),
                                label(combat_frame(records["on"], case, "on", COMBAT_IMPACT), f"{text}  ON")))
    grid = Image.new("RGB", (impact_rows[0].width, impact_rows[0].height * 2 + GAP), "black")
    for i, row in enumerate(impact_rows):
        grid.paste(row, (0, i * (row.height + GAP)))
    grid.save(OUT / "motionwarping-combat-impact.png", optimize=True)
    (DATA / "combat_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    for case, modes in summary.items():
        for mode, m in modes.items():
            print(f"{case:>5} {mode:<3} yaw {m['yaw_at_impact']:6.1f} (to enemy {m['yaw_to_enemy']:6.1f})"
                  f"  fist->enemy {m['fist_to_enemy_centre_cm']:6.1f}cm  root->target {m['root_to_target_cm']:6.1f}cm")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["mantle", "combat"], help="Export one example only")
    args = parser.parse_args()
    if args.only != "combat":
        export_mantle()
    if args.only != "mantle":
        export_combat()
