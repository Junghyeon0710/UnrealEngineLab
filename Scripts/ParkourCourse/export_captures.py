"""Turn the recorded PIE frames into the article's GIFs and stills and write the run summary.

Only real `Shot` frames (the player's own view with the HUD) and an editor viewport capture are used.
Processing is limited to resizing and cutting time ranges.
"""
from pathlib import Path
import json
import math
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/ParkourCourseLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/ParkourCourse"
GIF_SIZE = (544, 348)
OBSTACLES = {"Hurdle 70": (5885, 5925), "Wall 100": (6585, 6665), "Ledge 150": (7385, 7885), "Ledge 300": (7885, 8585)}


def load(name):
    record = json.loads((SOURCE / name / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    return record


def save_gif(frames, durations, path, colors=128, palette_frames=4, keep_colors=(), method=Image.Quantize.MEDIANCUT):
    palette_source = Image.new("RGB", (frames[0].width, frames[0].height * palette_frames))
    step = max(1, len(frames) // palette_frames)
    for i in range(palette_frames):
        palette_source.paste(frames[min(i * step, len(frames) - 1)], (0, frames[0].height * i))
    palette = palette_source.quantize(colors=colors - len(keep_colors), method=method)
    if keep_colors:
        # Debug lines are a few pixels wide, so the median cut drops their colours. Put them back in the palette.
        entries = palette.getpalette()[:3 * (colors - len(keep_colors))]
        palette.putpalette(entries + [c for rgb in keep_colors for c in rgb])
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    print(path.name, path.stat().st_size // 1024, "KB", len(frames), "frames")


def gif(name, t0, t1, path, step=0.1, speed=1.0, hold_last=1500, colors=128):
    record = load(name)
    frames, durations = [], []
    t = t0
    while t <= t1 + 1e-6:
        f = min(record["frames"], key=lambda f: abs(f["t"] - t))
        frames.append(Image.open(SOURCE / name / f["file"]).convert("RGB").resize(GIF_SIZE, Image.Resampling.LANCZOS))
        durations.append(round(step / speed * 1000))
        t += step
    durations[-1] = hold_last
    save_gif(frames, durations, path, colors)


def gif_windows(name, windows, path, size=(640, 410), frame_ms=133, hold_ms=700, crop=None, every=1, colors=256):
    """Every recorded frame inside the given time windows. Debug runs only record around the parts that matter.

    crop: (left, top, right, bottom) in the source frame, applied before resizing.
    """
    record = load(name)
    frames, durations = [], []
    for t0, t1 in windows:
        picked = [f for f in record["frames"] if t0 <= f["t"] <= t1][::every]
        frames += [Image.open(SOURCE / name / f["file"]).convert("RGB").crop(crop).resize(size, Image.Resampling.LANCZOS)
                   if crop else Image.open(SOURCE / name / f["file"]).convert("RGB").resize(size, Image.Resampling.LANCZOS)
                   for f in picked]
        durations += [frame_ms] * len(picked)
        durations[-1] = hold_ms
    debug_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (0, 255, 255), (255, 0, 255), (255, 255, 0), (255, 255, 255)]
    save_gif(frames, durations, path, colors=colors, palette_frames=8, keep_colors=debug_colors)


def side_by_side(left, right, t0, t1, path, size=(512, 328), frame_ms=133, hold_ms=1200, still_at=None, still_path=None):
    """Two runs with the same input, frame by frame at the same game time. Left and right are separated by a 6 px bar."""
    a, b = load(left), load(right)

    def pair(f):
        g = min(b["frames"], key=lambda g: abs(g["t"] - f["t"]))
        canvas = Image.new("RGB", (size[0] * 2 + 6, size[1]), "black")
        canvas.paste(Image.open(SOURCE / left / f["file"]).convert("RGB").resize(size, Image.Resampling.LANCZOS), (0, 0))
        canvas.paste(Image.open(SOURCE / right / g["file"]).convert("RGB").resize(size, Image.Resampling.LANCZOS), (size[0] + 6, 0))
        return canvas

    picked = [f for f in a["frames"] if t0 <= f["t"] <= t1]
    frames = [pair(f) for f in picked]
    durations = [frame_ms] * len(frames)
    durations[-1] = hold_ms
    # Max coverage keeps the small blue parts of the mannequin that median cut drops.
    save_gif(frames, durations, path, colors=256, palette_frames=8, method=Image.Quantize.MAXCOVERAGE)
    if still_at is not None:
        f = min(a["frames"], key=lambda f: abs(f["t"] - still_at))
        g = min(b["frames"], key=lambda g: abs(g["t"] - f["t"]))
        canvas = Image.new("RGB", (679 * 2 + 6, 435), "black")
        canvas.paste(Image.open(SOURCE / left / f["file"]).convert("RGB").resize((679, 435), Image.Resampling.LANCZOS), (0, 0))
        canvas.paste(Image.open(SOURCE / right / g["file"]).convert("RGB").resize((679, 435), Image.Resampling.LANCZOS), (685, 0))
        canvas.save(still_path, optimize=True)


def still(name, t, path, size):
    record = load(name)
    f = min(record["frames"], key=lambda f: abs(f["t"] - t))
    Image.open(SOURCE / name / f["file"]).convert("RGB").resize(size, Image.Resampling.LANCZOS).save(path, optimize=True)


def events(record):
    """When the run state, checkpoint count or fall count changed."""
    rows, last = [], None
    for s in record["samples"]:
        key = (s["state"], s["progress"], s["falls"])
        if key != last:
            rows.append({"t": s["t"], "state": s["state"], "checkpoints": s["progress"], "falls": s["falls"],
                         "elapsed": s["elapsed"], "location": s["location"]})
            last = key
    return rows


def obstacle_passes(record):
    """Highest point of the capsule while passing each obstacle, and how long it took."""
    out = {}
    for label, (x0, x1) in OBSTACLES.items():
        inside = [s for s in record["samples"] if s["location"] and x0 - 50 <= s["location"][0] <= x1 + 50]
        if inside:
            out[label] = {"enter_t": inside[0]["t"], "leave_t": inside[-1]["t"],
                          "max_capsule_z": max(s["location"][2] for s in inside),
                          "max_side_offset": max(abs(s["location"][1]) for s in inside)}
    return out


def montages(record):
    """Montages played during the run, with when they started and where the capsule was."""
    rows, last = [], None
    for s in record["samples"]:
        if s.get("montage") != last:
            if s.get("montage"):
                rows.append({"montage": s["montage"], "t": s["t"], "location": s["location"]})
            last = s.get("montage")
    return rows


def speeds(record, x0, x1):
    inside = [s for s in record["samples"] if s["location"] and x0 <= s["location"][0] <= x1]
    values = [math.hypot(*s["velocity"][:2]) for s in inside]
    return {"mean": sum(values) / len(values), "min": min(values), "max": max(values)} if values else None


SECTIONS = [("start floor", -800, 1500), ("ramp up 20", 1500, 2534), ("plateau", 2534, 3134), ("ramp down 30", 3134, 3785),
            ("cross slope entry", 3785, 4085), ("cross slope 20", 4085, 5285), ("obstacles", 5285, 8885)]


def section_of(x):
    return next((name for name, x0, x1 in SECTIONS if x0 <= x < x1), "off course")


def mm_timeline(record):
    """Database and animation Motion Matching was playing, each time either changed (and montages in between)."""
    rows, last = [], None
    for s in record["samples"]:
        anim = s.get("anim", {})
        key = (anim.get("CurrentSelectedDatabase"), anim.get("CurrentSelectedAnim"), s.get("montage"))
        if key != last:
            rows.append({"t": s["t"], "x": s["location"][0], "z": s["location"][2], "section": section_of(s["location"][0]),
                         "movement_mode": anim.get("MovementMode"), "database": key[0], "anim": key[1], "montage": key[2],
                         "valid_databases": anim.get("ValidDatabases")})
            last = key
    return rows


def foot_table(record):
    """Per section while on the ground: the lower ball bone each tick (the planted foot) and the pelvis drop."""
    out = {}
    for name, x0, x1 in SECTIONS[:6]:
        planted, pelvis = [], []
        for s in record["samples"]:
            feet, anim = s.get("feet"), s.get("anim", {})
            if not feet or anim.get("MovementMode") != "ON_GROUND" or not (x0 + 50 <= s["location"][0] < x1 - 50):
                continue
            heights = [feet[b] for b in ("ball_l", "ball_r") if feet.get(b) is not None]
            if len(heights) == 2:
                planted.append(min(heights))
                pelvis.append(feet["pelvis_above_capsule"])
        if planted:
            ordered = sorted(planted)
            out[name] = {"planted_ball_mean": sum(planted) / len(planted), "planted_ball_max": max(planted),
                         "planted_ball_min": min(planted), "planted_ball_p10": ordered[len(ordered) // 10],
                         "below_floor_ratio": sum(1 for v in planted if v < 0) / len(planted),
                         "pelvis_above_capsule_mean": sum(pelvis) / len(pelvis), "samples": len(planted)}
    return out


def warp_table(record):
    """For each traversal montage: the warp targets it registered and where the capsule ended up."""
    rows, current = [], None
    for s in record["samples"]:
        montage = s.get("montage")
        if montage and (current is None or current["montage"] != montage or s["t"] - current["last_t"] > 0.3):
            current = {"montage": montage, "start_t": s["t"], "start": s["location"], "targets": s.get("warp_targets"),
                       "last_t": s["t"], "end": s["location"]}
            rows.append(current)
        elif montage:
            current["last_t"], current["end"] = s["t"], s["location"]
            if s.get("warp_targets"):
                current["targets"] = s["warp_targets"]
    return rows


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    run = load("run_capture")
    run_events = events(run)
    start = next(e["t"] for e in run_events if e["state"] == "RUNNING")
    finish = next(e["t"] for e in run_events if e["state"] == "FINISHED")
    # 1. The slopes: ramp up, checkpoint 1, ramp down, cross slope. Real time.
    gif("run_capture", start - 0.3, 13.3, OUT / "parkour-slopes.gif", step=0.15, speed=1.5)
    # 2. The obstacles to the finish line. Real time.
    gif("run_capture", 16.2, finish + 1.6, OUT / "parkour-obstacles.gif", step=0.1, colors=104)
    # 3. Falling off the plateau and coming back at checkpoint 1. Real time.
    fall = load("fall_capture")
    first_fall = next(e["t"] for e in events(fall) if e["falls"] == 1)
    gif("fall_capture", first_fall - 2.2, first_fall + 0.9, OUT / "parkour-fall-respawn.gif", step=0.1)
    # 4. Stills: the finish screen and the whole course in the editor.
    still("run_capture", finish + 0.8, OUT / "parkour-finish.png", (1086, 696))
    Image.open(SOURCE / "course_overview.png").convert("RGB").resize((1086, 696), Image.Resampling.LANCZOS).save(
        OUT / "parkour-course-overview.png", optimize=True)
    # 5. One GIF per system. Motion Matching: standing to running at the start (real time).
    #    Control Rig and Motion Warping: their debug drawing, played at half speed.
    # Motion Matching debug text (a.AnimNode.MotionMatching.DebugDrawInfo 1): the start and the hurdle. The frames are
    # whole editor-window shots (Shot showui), cropped around the character and the text.
    mm_crop = (380, 300, 1220, 1000)
    gif_windows("debug_motion_matching", [(0.0, 3.3), (16.9, 18.7)], OUT / "parkour-mm-debug.gif", size=(720, 600),
                frame_ms=200, hold_ms=1200, crop=mm_crop, every=2, colors=96)
    # One plain jump on the start floor, filmed from the side with the same debug text (used in MotionMatching.md).
    gif_windows("debug_mm_jump", [(3.3, 5.8)], OUT / "motionmatching-jump.gif", size=(720, 574), frame_ms=200, hold_ms=1200,
                crop=(330, 330, 1170, 1000), colors=96)
    record = load("debug_motion_matching")
    f = min(record["frames"], key=lambda f: abs(f["t"] - 0.47))
    Image.open(SOURCE / "debug_motion_matching" / f["file"]).convert("RGB").crop((380, 300, 1180, 980)).save(
        OUT / "parkour-mm-debug.png", optimize=True)
    gif_windows("debug_control_rig", [(6.5, 7.5), (12.4, 13.6)], OUT / "parkour-cr-debug.gif")
    gif_windows("debug_motion_warping", [(17.0, 18.4), (20.9, 22.4)], OUT / "parkour-mw-debug.gif")
    # Control Rig off (left) and on (right) on the 30° ramp down, filmed from the side. The still is where the off run's
    # planted foot sinks deepest (frame at 11.47 s, ball_r -16.4 cm).
    side_by_side("side_ramp_down_rig_off", "side_ramp_down_rig_on", 10.1, 12.3, OUT / "parkour-cr-ramp-off-on.gif",
                 still_at=11.48, still_path=OUT / "parkour-cr-ramp-off-on.png")
    foot_off = load("run_foot_placement_off")
    summary_systems = {"motion_matching": mm_timeline(run), "foot_placement_on": foot_table(run),
                       "foot_placement_off": foot_table(foot_off), "motion_warping": warp_table(run),
                       "finish_with_foot_placement_off": next((e["elapsed"] for e in events(foot_off) if e["state"] == "FINISHED"), None)}
    (DATA / "systems.json").write_text(json.dumps(summary_systems, indent=1), encoding="utf-8")
    for row in summary_systems["motion_matching"]:
        print(f"mm {row['t']:6.2f}s x{row['x']:6.0f} {row['section']:<18} {row['movement_mode']:<11} {row['database']} | {row['anim']} | {row['montage']}")
    for state in ("on", "off"):
        for section, v in summary_systems[f"foot_placement_{state}"].items():
            print(f"feet {state:<3} {section:<18} p10 {v['planted_ball_p10']:6.1f} min {v['planted_ball_min']:6.1f} below {v['below_floor_ratio']*100:5.1f}% pelvis {v['pelvis_above_capsule_mean']:6.1f} n={v['samples']}")
    for row in summary_systems["motion_warping"]:
        print("warp", round(row["start_t"], 2), row["montage"], [(t["name"], [round(c) for c in t["location"]]) for t in row["targets"] or []],
              "end", [round(c) for c in row["end"]])
    summary = {"run": {"events": run_events, "obstacles": obstacle_passes(run), "jumps": run["jumps"], "montages": montages(run),
                       "speed_start_floor": speeds(run, 200, 1400), "speed_ramp_up": speeds(run, 1600, 2400),
                       "speed_ramp_down": speeds(run, 3200, 3700), "speed_cross_slope": speeds(run, 4200, 5200)},
               "fall": {"events": events(fall)}}
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    for e in run_events:
        print(f"{e['t']:6.2f}s {e['state']:<9} checkpoints {e['checkpoints']} falls {e['falls']} elapsed {e['elapsed']:.2f}")
    print(json.dumps(summary["run"]["obstacles"], indent=1))
    for row in summary["run"]["montages"]:
        print(f"montage {row['t']:6.2f}s {row['montage']} at {[round(v) for v in row['location']]}")
    for key in ("speed_start_floor", "speed_ramp_up", "speed_ramp_down", "speed_cross_slope"):
        print(key, {k: round(v) for k, v in summary["run"][key].items()})
    for e in summary["fall"]["events"]:
        print(f"fall {e['t']:6.2f}s {e['state']:<9} checkpoints {e['checkpoints']} falls {e['falls']} at {[round(v) for v in e['location']]}")
