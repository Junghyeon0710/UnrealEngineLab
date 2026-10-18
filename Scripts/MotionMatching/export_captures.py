"""Turn the recorded PIE frames into the article's GIFs and write the measurements.

Only real `Shot` frames are used. Processing is limited to cropping, resizing, placing runs
side by side, and a label with the recorded AnimBP values for that frame.
"""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/MotionMatchingLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/MotionMatching"
CROP = (329, 110, 1029, 800)        # the follow camera keeps the character in the middle of the 1358x870 frame
GAP = 6
FONT = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 15)
FONT_BIG = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 17)
PIVOT = (2.3, 3.6)                 # input reversed during this window
FOOT_CONTACT = 4.0                 # a foot counts as planted within this height above its lowest point
MODES = ("dense", "sparse", "xsparse", "sm")


def load(name):
    record = json.loads((SOURCE / name / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    return record


def played(sample):
    """Animation actually driving the pose: search result for motion matching, chooser result for the state machine."""
    if sample.get("UseExperimentalStateMachine"):
        return sample.get("BlendStackAnim")
    return sample.get("CurrentSelectedAnim")


def frame(record, name, t, size):
    f = min(record["frames"], key=lambda f: abs(f["t"] - t))
    image = Image.open(SOURCE / name / f["file"]).convert("RGB").crop(CROP)
    return image.resize(size, Image.Resampling.LANCZOS), f


def sample_at(record, t):
    return min(record["samples"], key=lambda s: abs(s["t"] - t))


def label(image, lines):
    draw = ImageDraw.Draw(image)
    y = 8
    for i, text in enumerate(lines):
        font = FONT_BIG if i == 0 else FONT
        draw.text((10, y), text, font=font, fill="white", stroke_width=3, stroke_fill="black")
        y += 22 if i == 0 else 19
    return image


def describe(sample, title):
    if sample.get("UseExperimentalStateMachine"):
        return [title, f"state  {sample.get('StateMachineState', '')}", f"anim   {sample.get('BlendStackAnim', '')}"]
    database = (sample.get("CurrentSelectedDatabase") or "").replace("PSD_", "")
    return [title, f"db     {database}", f"anim   {sample.get('CurrentSelectedAnim', '')}"]


def side_by_side(panels):
    width = sum(p.width for p in panels) + GAP * (len(panels) - 1)
    canvas = Image.new("RGB", (width, panels[0].height), "black")
    x = 0
    for p in panels:
        canvas.paste(p, (x, 0))
        x += p.width + GAP
    return canvas


def save_gif(frames, durations, path, colors=128):
    palette_source = Image.new("RGB", (frames[0].width, frames[0].height * 4))
    step = max(1, len(frames) // 4)
    for i in range(4):
        palette_source.paste(frames[min(i * step, len(frames) - 1)], (0, frames[0].height * i))
    palette = palette_source.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    print(path.name, path.stat().st_size // 1024, "KB")


def gif(names_titles, t0, t1, path, size, step=0.05, speed=1.0, colors=128):
    records = {name: load(name) for name, _ in names_titles}
    frames, durations = [], []
    t = t0
    while t <= t1 + 1e-6:
        panels = []
        for name, title in names_titles:
            image, _ = frame(records[name], name, t, size)
            panels.append(label(image, describe(sample_at(records[name], t), title)))
        frames.append(side_by_side(panels))
        durations.append(round(step / speed * 1000))
        t += step
    durations[-1] = 1200
    save_gif(frames, durations, path, colors)


def timeline(record):
    """Consecutive spans of what was playing, with the input at the start of each span."""
    rows, current = [], None
    for s in record["samples"]:
        key = (s.get("CurrentSelectedDatabase") if not s.get("UseExperimentalStateMachine") else s.get("StateMachineState"), played(s))
        if key != current:
            if rows:
                rows[-1]["end"] = s["t"]
            rows.append({"start": s["t"], "end": None, "input_yaw": s["input_yaw"], "group": key[0], "anim": key[1],
                         "speed": math.hypot(*s["velocity"][:2]), "yaw": s["yaw"]})
            current = key
    rows[-1]["end"] = record["samples"][-1]["t"]
    return rows


def foot_skate(record, t0, t1):
    """Mean horizontal speed of each ball bone while it is within FOOT_CONTACT of its lowest height."""
    samples = record["samples"]
    result = {}
    for foot in ("ball_l", "ball_r"):
        floor = min(s["feet"][foot][2] for s in samples)
        speeds = []
        for a, b in zip(samples, samples[1:]):
            dt = b["t"] - a["t"]
            if t0 <= b["t"] < t1 and dt > 0 and a["feet"][foot][2] < floor + FOOT_CONTACT and b["feet"][foot][2] < floor + FOOT_CONTACT:
                speeds.append(math.dist(a["feet"][foot][:2], b["feet"][foot][:2]) / dt)
        result[foot] = sum(speeds) / len(speeds) if speeds else None
    return result


def switches(record, t0, t1):
    count, previous = 0, None
    for s in record["samples"]:
        current = played(s)
        if previous is not None and current != previous and t0 <= s["t"] < t1:
            count += 1
        previous = current
    return count


def candidates(record):
    """When the chooser's database list or the selected animation changes."""
    rows, current = [], None
    for sample in record["samples"]:
        key = (tuple(sample.get("ValidDatabases") or []), sample.get("CurrentSelectedAnim"))
        if key != current:
            rows.append({"t": sample["t"], "input_yaw": sample["input_yaw"], "valid_databases": list(key[0]),
                         "selected_database": sample.get("CurrentSelectedDatabase"), "selected_anim": key[1]})
            current = key
    return rows


def measure(mode):
    runs = []
    for i in (1, 2, 3):
        record = load(f"mm_{mode}_r{i}")
        skate = foot_skate(record, *PIVOT)
        runs.append({"skate_ball_l": skate["ball_l"], "skate_ball_r": skate["ball_r"],
                     "skate_mean": (skate["ball_l"] + skate["ball_r"]) / 2,
                     "switches_in_pivot": switches(record, *PIVOT),
                     "pivot_anims": sorted({played(s) for s in record["samples"] if PIVOT[0] <= s["t"] < PIVOT[1]}),
                     "samples": len(record["samples"])})
    mean = lambda key: sum(r[key] for r in runs) / len(runs)
    return {"runs": runs, "skate_mean": mean("skate_mean"), "skate_ball_l": mean("skate_ball_l"),
            "skate_ball_r": mean("skate_ball_r"), "switches_in_pivot": mean("switches_in_pivot")}


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    titles = {"dense": "Motion Matching  Dense", "sparse": "Motion Matching  Sparse",
              "xsparse": "Motion Matching  Extreme Sparse", "sm": "State Machine (experimental)"}
    # 1. Whole run with Dense data, real time.
    gif([("mm_dense", titles["dense"])], 0.3, 4.7, OUT / "motionmatching-run-dense.gif", (400, 394), step=0.08, colors=80)
    # 2. The reversal with less data, half speed.
    gif([("mm_dense", titles["dense"]), ("mm_xsparse", titles["xsparse"])], 2.1, 3.7,
        OUT / "motionmatching-pivot-dense-vs-xsparse.gif", (380, 374), speed=0.5, colors=80)
    # 3. Four moments of the Dense run as a still: idle, start, reversal, stop.
    record = load("mm_dense")
    moments = []
    for t in (0.3, 1.2, 2.6, 4.0):
        image, _ = frame(record, "mm_dense", t, (430, 424))
        moments.append(label(image, describe(sample_at(record, t), f"t = {t:.1f}s")))
    top, bottom = side_by_side(moments[:2]), side_by_side(moments[2:])
    still = Image.new("RGB", (top.width, top.height * 2 + GAP), "black")
    still.paste(top, (0, 0))
    still.paste(bottom, (0, top.height + GAP))
    still.save(OUT / "motionmatching-run-moments.png", optimize=True)
    summary = {"segments": load("mm_dense")["segments"], "pivot_window": PIVOT, "foot_contact_cm": FOOT_CONTACT,
               "timelines": {mode: timeline(load(f"mm_{mode}")) for mode in MODES},
               "candidates_dense_r1": candidates(load("mm_dense_r1")),
               "measurements": {mode: measure(mode) for mode in MODES}}
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    # Values read in the editor: schema channels (run_tests.py) and database statistics (Statistics tab).
    for extra in ("schema.json", "database_stats.json"):
        if (SOURCE / extra).exists():
            (DATA / extra).write_bytes((SOURCE / extra).read_bytes())
    for row in summary["candidates_dense_r1"]:
        print(f"   t {row['t']:.2f} in {str(row['input_yaw']):>5} {row['selected_anim']:<34} {row['valid_databases']}")
    for mode in MODES:
        m = summary["measurements"][mode]
        print(f"{mode:>8} skate L {m['skate_ball_l']:6.1f} R {m['skate_ball_r']:6.1f} mean {m['skate_mean']:6.1f} cm/s"
              f"  switches {m['switches_in_pivot']:.1f}  pivot anims {m['runs'][0]['pivot_anims']}")
    for mode in MODES:
        print("--", mode)
        for row in summary["timelines"][mode]:
            print(f"   {row['start']:.2f}-{row['end']:.2f} in {str(row['input_yaw']):>5} {str(row['group']):<36} {row['anim']}")
