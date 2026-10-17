"""Encode real Unreal PNG frames. No rendered or generated diagram is used."""
from pathlib import Path
import json
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/MotionWarpingLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/MotionWarping"
DATA.mkdir(parents=True, exist_ok=True)
if (SOURCE / "montages.json").exists():
    (DATA / "montages.json").write_bytes((SOURCE / "montages.json").read_bytes())


def export_case(name):
    folder = SOURCE / name
    record = json.loads((folder / "measurements.json").read_text())
    assert not record.get("error"), record.get("error")
    assert record["motion_warping_disabled"] == int(name.endswith("_off"))
    assert record["trigger_result"] == "(False, False)", record["trigger_result"]
    assert "UEDPIE_" in record["capture_audit"]["world"]
    assert "CameraActor_" in record["capture_audit"]["view_target"]
    assert record["setup"]["bounds_extent"][2] == 50.0
    frames, durations = [], []
    for i, frame in enumerate(record["frames"]):
        with Image.open(folder / frame["file"]) as im:
            im = im.convert("RGB")
            if i == 0:
                crop = im.getbbox()  # Remove the camera's black letterboxing only.
            im = im.crop(crop)
            im.thumbnail((960, 540), Image.Resampling.LANCZOS)
            frames.append(im.copy())
        next_t = record["frames"][i+1]["t"] if i+1 < len(record["frames"]) else frame["t"] + .6
        durations.append(max(20, round((next_t-frame["t"])*100)*10))
    palette_source = Image.new("RGB", (160 * len(frames), 90))
    for i, im in enumerate(frames):
        palette_source.paste(im.resize((160, 90)), (160*i, 0))
    palette = palette_source.quantize(colors=192)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.NONE) for im in frames]
    path = OUT / ("motionwarping-gas-" + name.replace("_", "-") + ".gif")
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    active = [s for s in record["samples"] if s["position"] is not None]
    montages = sorted({s["montage"] for s in active})
    assert len(montages) == 1, montages
    result = {"case": name, "montage": montages[0], "start": record["start"],
              "capture_time_dilation": record["capture_time_dilation"],
              "capsule_half_height": record["capsule_half_height"],
              "trigger_result": record["trigger_result"], "frames": len(frames),
              "frame_times": [f["t"] for f in record["frames"]],
              "gif": path.name, "gif_bytes": path.stat().st_size, "samples": []}
    montage_data = json.loads((DATA / "montages.json").read_text(encoding="utf-8"))[montages[0]]
    windows = montage_data["windows"]
    for target in ("FrontLedge", "BackFloor"):
        end = max(w["end"] for w in windows if w["warp_target_name"] == target)
        sample = min(active, key=lambda s: abs(s["position"]-end))
        point = sample["attach"] if target == "FrontLedge" else [sample["location"][0], sample["location"][1], sample["location"][2]-record["capsule_half_height"]]
        goal = sample["targets"][target]
        result["samples"].append({"target": target, "window_end": end, "sample_montage_position": sample["position"],
                                  "point": point, "target_location": goal,
                                  "error_3d_cm": math.dist(point, goal), "error_xy_cm": math.dist(point[:2], goal[:2])})
    # Public evidence contains the actual numeric samples, not editor logs or source assets.
    (DATA / (name + ".json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
    return result, frames, record


def comparison(depth, cases):
    """Align existing screenshots by time since traversal; never synthesize poses."""
    font = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 21)
    small = ImageFont.truetype("C:/Windows/Fonts/malgun.ttf", 16)
    panels, durations = [], []
    manifest = []
    for index in range(25):
        time = index * .08 - .32
        panel = Image.new("RGB", (1280, 440), "#171c24")
        draw = ImageDraw.Draw(panel)
        selected = {}
        for side, suffix in enumerate(("off", "on")):
            result, images, record = cases[depth + "_" + suffix]
            trigger = record.get("trigger_time", next(s["t"] for s in record["samples"] if s["montage"]))
            chosen = min(range(len(images)), key=lambda i: abs(record["frames"][i]["t"] - trigger - time))
            image = ImageOps.contain(images[chosen], (632, 356), Image.Resampling.LANCZOS)
            panel.paste(image, (side * 640 + (640-image.width)//2, 48 + (356-image.height)//2))
            color = "#ffb26b" if suffix == "off" else "#67e4cb"
            draw.text((side*640+18, 10), "Motion Warping " + suffix.upper(), font=font, fill=color)
            selected[suffix] = {"file": record["frames"][chosen]["file"], "recorded_game_time": record["frames"][chosen]["t"], "since_trigger": record["frames"][chosen]["t"]-trigger}
        draw.line((640, 0, 640, 440), fill="#617086", width=2)
        draw.text((18, 411), f"높이 100cm · 두께 {depth[5:]}cm | 실제 PIE · 0.5배 재생 | 시작 후 {time:.2f}s에 가까운 캡처", font=small, fill="#e4ebf4")
        panels.append(panel)
        durations.append(1200 if index == 9 else 800 if index in (14, 24) else 160)
        manifest.append({"aligned_time_since_trigger": time, "selected": selected})
    palette_source = Image.new("RGB", (256*len(panels), 88))
    for index, frame in enumerate(panels):
        palette_source.paste(frame.resize((256,88)), (256*index,0))
    palette = palette_source.quantize(colors=224)
    indexed = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in panels]
    indexed[0].save(OUT / f"motionwarping-gas-{depth}-comparison.gif", save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True, disposal=1)
    # A still close to the contact phase makes the real hand/obstacle relation readable.
    contact = Image.new("RGB", (1280, 620), "#171c24")
    draw = ImageDraw.Draw(contact)
    contact_manifest = {}
    for side, suffix in enumerate(("off", "on")):
        result, images, record = cases[depth + "_" + suffix]
        end = next(s["window_end"] for s in result["samples"] if s["target"] == "FrontLedge")
        sample = min((s for s in record["samples"] if s["position"] is not None), key=lambda s: abs(s["position"]-end))
        chosen = min(range(len(images)), key=lambda i: abs(record["frames"][i]["t"]-sample["t"]))
        # Same normalized crop on both images: actual contact area, no geometry edits.
        im = images[chosen]
        crop = im.crop((int(im.width*.34), int(im.height*.16), int(im.width*.76), int(im.height*.63)))
        crop = ImageOps.contain(crop, (624, 490), Image.Resampling.LANCZOS)
        contact.paste(crop, (side*640+(640-crop.width)//2, 64+(490-crop.height)//2))
        draw.text((side*640+18, 12), "Motion Warping "+suffix.upper()+" · 접촉 구간 확대", font=font, fill="#ffb26b" if suffix=="off" else "#67e4cb")
        draw.text((side*640+18, 565), f"실제 캡처 t={record['frames'][chosen]['t']:.3f}s · Window 끝에 인접한 이미지", font=small, fill="#e4ebf4")
        contact_manifest[suffix] = {"frame": record["frames"][chosen], "nearest_sample_montage_position": sample["position"], "window_end": end}
    draw.line((640,0,640,620), fill="#617086", width=2)
    contact.save(OUT / f"motionwarping-gas-{depth}-contact-comparison.png", optimize=True)
    (DATA / f"{depth}_comparison_frames.json").write_text(json.dumps({"frames":manifest,"contact":contact_manifest},indent=2),encoding="utf-8")


if __name__ == "__main__":
    summary = []
    cases = {}
    for name in ["depth50_on", "depth50_off", "depth20_on", "depth20_off"]:
        result, frames, record = export_case(name)
        cases[name] = (result, frames, record)
        summary.append(result)
        print(name, "frames", result["frames"], "bytes", result["gif_bytes"],
              [(s["target"], round(s["sample_montage_position"], 4), round(s["error_3d_cm"], 3), round(s["error_xy_cm"], 3)) for s in result["samples"]])
        if name == "depth50_on":
            nearest = min(range(len(record["frames"])), key=lambda i: abs(record["frames"][i]["t"]-.8))
            frames[nearest].save(OUT / "motionwarping-gas-hurdle-contact.png", optimize=True)
    for depth in ("depth50", "depth20"):
        assert len({r["montage"] for r in summary if r["case"].startswith(depth)}) == 1, "Each ON/OFF pair must use the same montage"
        comparison(depth, cases)
    (DATA / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Actual PIE evidence exported.")
