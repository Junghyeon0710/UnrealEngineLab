"""Turn the recorded PIE frames into the article's images and write the measurements.

Only real `Shot` frames are used. Processing is limited to cropping, resizing, placing runs
side by side, and a one-line label per panel.
"""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/ControlRigLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/ControlRig"
CROP = (319, 0, 1039, 870)           # the follow camera keeps the character in the middle of the 1358x870 frame
GAP = 6
FONT = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 17)
SLOPES = (0, 10, 20, 30, 40)
LOOKAT_CROP = (180, 90, 1180, 875)    # fixed camera in LookAtPOI_Level: the pawn and the walker's half circle


def load(name):
    record = json.loads((SOURCE / name / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    return record


def label(image, text):
    draw = ImageDraw.Draw(image)
    draw.text((10, 8), text, font=FONT, fill="white", stroke_width=3, stroke_fill="black")
    return image


def side_by_side(panels):
    width = sum(p.width for p in panels) + GAP * (len(panels) - 1)
    canvas = Image.new("RGB", (width, panels[0].height), "black")
    x = 0
    for p in panels:
        canvas.paste(p, (x, 0))
        x += p.width + GAP
    return canvas


def still(name, size):
    record = load(name)
    image = Image.open(SOURCE / name / record["frames"][0]["file"]).convert("RGB").crop(CROP)
    return image.resize(size, Image.Resampling.LANCZOS)


def save_gif(frames, durations, path, colors=96):
    palette_source = Image.new("RGB", (frames[0].width, frames[0].height * 4))
    step = max(1, len(frames) // 4)
    for i in range(4):
        palette_source.paste(frames[min(i * step, len(frames) - 1)], (0, frames[0].height * i))
    palette = palette_source.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    print(path.name, path.stat().st_size // 1024, "KB")


def gif(names_titles, t0, t1, path, size, step=0.05, speed=1.0, crop=CROP, colors=96):
    records = {name: load(name) for name, _ in names_titles}
    frames, durations = [], []
    t = t0
    while t <= t1 + 1e-6:
        panels = []
        for name, title in names_titles:
            f = min(records[name]["frames"], key=lambda f: abs(f["t"] - t))
            image = Image.open(SOURCE / name / f["file"]).convert("RGB").crop(crop).resize(size, Image.Resampling.LANCZOS)
            panels.append(label(image, title))
        frames.append(side_by_side(panels))
        durations.append(round(step / speed * 1000))
        t += step
    durations[-1] = 1200
    save_gif(frames, durations, path, colors)


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def gaps(record):
    """Mean height of each foot bone above the floor right under it, over the recorded second."""
    out = {}
    for bone in ("ball_l", "ball_r", "foot_l", "foot_r"):
        out[bone] = mean([s["feet"][bone][2] - s["feet"][bone][3] for s in record["samples"] if s["feet"][bone][3] is not None])
    out["pelvis_above_actor"] = mean([s["pelvis"][2] - s["location"][2] for s in record["samples"]])
    return out


def walk_contacts(record, t0=0.6, t1=2.2):
    """While walking: the lower ball bone each frame (the planted foot) and how far it is from the floor."""
    lows = []
    for s in record["samples"]:
        if t0 <= s["t"] < t1:
            heights = [s["feet"][b][2] - s["feet"][b][3] for b in ("ball_l", "ball_r") if s["feet"][b][3] is not None]
            if len(heights) == 2:
                lows.append(min(heights))
    return {"planted_ball_mean": mean(lows), "planted_ball_min": min(lows), "planted_ball_max": max(lows), "samples": len(lows)}


def relative_yaw(axis, facing):
    yaw = math.degrees(math.atan2(axis[1], axis[0])) - facing
    return (yaw + 180.0) % 360.0 - 180.0


def lookat_table(record, angles=(90, 60, 30, 0, -30, -60, -90)):
    """While walking: how far the pelvis, upper spine and head had turned when the walker crossed each angle."""
    facing = record["facing_yaw"]
    walking = [s for s in record["samples"] if s["walking"]]
    rows = []
    for angle in angles:
        sample = min(walking, key=lambda s: abs(s["walker_angle"] - angle))
        rows.append({"walker_angle": angle, "t": sample["t"],
                     **{bone: relative_yaw(sample["bones"][bone]["y"], facing) for bone in ("pelvis", "spine_05", "head")}})
    end = record["samples"][-1]
    rows.append({"walker_angle": "end " + str(round(end["walker_angle"])), "t": end["t"],
                 **{bone: relative_yaw(end["bones"][bone]["y"], facing) for bone in ("pelvis", "spine_05", "head")}})
    return rows


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    # 1. 30 degree slope, standing across it: Leg IK only vs the foot placement rig.
    pair = side_by_side([label(still("slope_30_off", (390, 471)), "Control Rig OFF"),
                         label(still("slope_30_on", (390, 471)), "Control Rig ON")])
    pair.save(OUT / "controlrig-slope-30-off-on.png", optimize=True)
    # 2. The rig's own debug drawing in PIE (cyan: animated legs, green: after the rig).
    still("debug_30", (540, 653)).save(OUT / "controlrig-slope-30-debug.png", optimize=True)
    # 3. Walking across the 30 degree part, OFF and ON side by side, half speed.
    gif([("walk_30_off", "Control Rig OFF"), ("walk_30_on", "Control Rig ON")], 0.2, 2.6,
        OUT / "controlrig-walk-30.gif", (340, 411), step=0.05, speed=0.5)
    summary = {"slopes": {}, "walk_30": {}}
    for degrees in SLOPES:
        summary["slopes"][degrees] = {state: gaps(load(f"slope_{degrees}_{state}")) for state in ("on", "off")}
    for state in ("on", "off"):
        summary["walk_30"][state] = walk_contacts(load(f"walk_30_{state}"))
    (DATA / "foot_placement_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    for extra in ("rig_structure.json", "lookat_data_asset.json"):
        if (SOURCE / extra).exists():
            (DATA / extra).write_bytes((SOURCE / extra).read_bytes())
    # 4. LookAtPOI: the walker circles the pawn, OFF and ON side by side, real time.
    if (SOURCE / "lookat_on").exists() and (SOURCE / "lookat_off").exists():
        gif([("lookat_off", "LookAtPOI OFF"), ("lookat_on", "LookAtPOI ON")], 0.0, 5.9,
            OUT / "controlrig-lookat-walk.gif", (400, 314), step=0.1, speed=1.0, crop=LOOKAT_CROP, colors=160)
        lookat = {state: lookat_table(load(f"lookat_{state}")) for state in ("on", "off")}
        (DATA / "lookat_summary.json").write_text(json.dumps(lookat, indent=1), encoding="utf-8")
        for state, rows in lookat.items():
            print("lookat", state)
            for row in rows:
                print(f"   walker {str(row['walker_angle']):>8}  pelvis {row['pelvis']:6.1f}  spine_05 {row['spine_05']:6.1f}  head {row['head']:6.1f}")
    print(f"{'slope':>5} {'state':>5} {'ball_l':>7} {'ball_r':>7} {'foot_l':>7} {'foot_r':>7} {'pelvis':>7}")
    for degrees, states in summary["slopes"].items():
        for state, g in states.items():
            print(f"{degrees:>5} {state:>5} {g['ball_l']:7.1f} {g['ball_r']:7.1f} {g['foot_l']:7.1f} {g['foot_r']:7.1f} {g['pelvis_above_actor']:7.1f}")
    print(json.dumps(summary["walk_30"], indent=1))
