"""Turn the MVVM lab recordings into the article's GIF and the measurement summary (Docs/UE/MVVM.md).

Frames are 'Shot showui' captures of the editor window during PIE. Processing is cropping the PIE viewport
around the widgets and resizing.
"""
from pathlib import Path
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/MVVMLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/MVVM"
CROP = (20, 150, 710, 630)   # the three widgets and the counters, in editor-window pixels
KEYS = ("frames", "model_changes", "classic_binding_calls", "mvvm_getter_calls")


def load(name):
    record = json.loads((SOURCE / name / "measurements.json").read_text())
    assert not record.get("error"), record["error"]
    return record


def at(record, t):
    return min(record["samples"], key=lambda s: abs(s["t"] - t))


def delta(a, b):
    return {k: b[k] - a[k] for k in KEYS} | {"seconds": round(b["t"] - a["t"], 2)}


def demo_gif(name, path, scale=0.9, frame_ms=200, hold_ms=1500):
    record = load(name)
    size = (round((CROP[2] - CROP[0]) * scale), round((CROP[3] - CROP[1]) * scale))
    frames = [Image.open(SOURCE / name / f["file"]).convert("RGB").crop(CROP).resize(size, Image.Resampling.LANCZOS)
              for f in record["frames"]]
    palette_source = Image.new("RGB", (size[0], size[1] * 4))
    for i in range(4):
        palette_source.paste(frames[i * (len(frames) - 1) // 3], (0, size[1] * i))
    palette = palette_source.quantize(colors=128, method=Image.Quantize.MAXCOVERAGE)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    durations = [frame_ms] * len(frames)
    durations[-1] = hold_ms
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True)
    print(path.name, path.stat().st_size // 1024, "KB", len(frames), "frames")


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    demo_gif("demo_click", OUT / "mvvm-demo.gif")

    measure = load("measure")          # 0-10 s nothing changes, 10 s demo starts, 18 s heal through the ViewModel
    idle = delta(at(measure, 0.05), at(measure, 9.95))
    demo = delta(at(measure, 9.95), at(measure, 19.95))
    burst = load("burst_auto")         # three heals in the same tick at 9.5 s
    before, after = at(burst, 9.48), at(burst, 9.52)
    click = load("demo_click")         # the real HEAL button of View A pressed at about 11.4 s
    heal = next(s for s in click["samples"] if s["health"] > 28 and s["t"] > 10)
    pre = max((s for s in click["samples"] if s["t"] < heal["t"]), key=lambda s: s["t"])
    summary = {
        "fps": 30,
        "idle_10s": idle,
        "demo_10s": demo,
        "per_frame_classic_calls": round(demo["classic_binding_calls"] / demo["frames"], 2),
        "burst_three_heals_one_tick": {"mvvm_getter_calls": after["mvvm_getter_calls"] - before["mvvm_getter_calls"],
                                       "model_changes": after["model_changes"] - before["model_changes"]},
        "heal_button_click": {"t": round(heal["t"], 2), "health_before": pre["health"], "health_after": heal["health"],
                              "mvvm_getter_calls": heal["mvvm_getter_calls"] - pre["mvvm_getter_calls"]},
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
