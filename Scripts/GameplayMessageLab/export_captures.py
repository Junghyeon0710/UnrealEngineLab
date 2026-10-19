"""Turn the GameplayMessage lab recordings into the article's images and the measurement summary (Docs/UE/GameplayMessage.md).

Inputs (Saved/GameplayMessageLab)
  demo/          'Shot showui' frames of the editor window during PIE (run_tests.py)
  tests.json     order, mismatch and benchmark results (run_tests.py)
  editor/        SlateInspector screenshots of the editor window
                   wbp_graph.png    WBP_GMLabFeed event graph
                   output_log.png   output log filtered by LogGameplayMessageSubsystem after the mismatch test
Processing is cropping and resizing only.
"""
from pathlib import Path
import json
import statistics
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Saved/GameplayMessageLab"
OUT = ROOT / "Docs/UE/Images"
DATA = ROOT / "Docs/UE/Evidence/GameplayMessage"
VIEWPORT = (4, 135, 1362, 1003)      # PIE viewport inside the editor window
GRAPH = (480, 128, 1765, 850)         # event graph of WBP_GMLabFeed
LOG = (22, 422, 1782, 512)            # search box and the four log lines
# Shot lines and the accolade text are small, so they are added to the palette as they are.
KEEP_COLORS = [(40, 120, 255), (255, 60, 40), (255, 204, 51)]


def demo_gif(path, scale=0.7, frame_ms=250, hold_ms=2000):
    record = json.loads((SOURCE / "demo/measurements.json").read_text())
    assert not record.get("error"), record["error"]
    size = (round((VIEWPORT[2] - VIEWPORT[0]) * scale), round((VIEWPORT[3] - VIEWPORT[1]) * scale))
    frames = [Image.open(SOURCE / "demo" / f["file"]).convert("RGB").crop(VIEWPORT).resize(size, Image.Resampling.LANCZOS)
              for f in record["frames"]]
    samples = 6
    palette_source = Image.new("RGB", (size[0], size[1] * samples))
    for i in range(samples):
        palette_source.paste(frames[i * (len(frames) - 1) // (samples - 1)], (0, size[1] * i))
    colors = palette_source.quantize(colors=64 - len(KEEP_COLORS), method=Image.Quantize.MAXCOVERAGE).getpalette()
    palette = Image.new("P", (1, 1))
    palette.putpalette(colors[:(64 - len(KEEP_COLORS)) * 3] + [c for color in KEEP_COLORS for c in color])
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    durations = [frame_ms] * len(frames)
    durations[-1] = hold_ms
    indexed[0].save(path, save_all=True, append_images=indexed[1:], duration=durations, loop=0, optimize=True)
    print(path.name, path.stat().st_size // 1024, "KB", len(frames), "frames")


def crop(name, box, path):
    Image.open(SOURCE / "editor" / name).convert("RGB").crop(box).save(path, optimize=True)
    print(path.name, Image.open(path).size)


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    demo_gif(OUT / "gameplaymessage-demo.gif")
    crop("wbp_graph.png", GRAPH, OUT / "gameplaymessage-listen-node.png")
    crop("output_log.png", LOG, OUT / "gameplaymessage-mismatch-log.png")

    tests = json.loads((SOURCE / "tests.json").read_text())
    benchmark = []
    for runs in tests["benchmark"]:
        message = statistics.median(r["message_us"] for r in runs)
        delegate = statistics.median(r["delegate_us"] for r in runs)
        benchmark.append({"listeners": runs[0]["listeners"], "broadcasts": runs[0]["broadcasts"],
                          "gameplay_message_us": round(message, 3), "multicast_delegate_us": round(delegate, 3),
                          "ratio": round(message / delegate, 1),
                          "all_delivered": all(r["message_received"] == r["delegate_received"] == r["broadcasts"] * r["listeners"]
                                               for r in runs)})
    summary = {
        "demo": {"fps": 30, "shot_interval_s": 0.6, "counters": tests["demo_counters"]},
        "order": tests["order"],
        "mismatch": tests["mismatch"],
        "benchmark_median_of_3": benchmark,
    }
    (DATA / "summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1, ensure_ascii=False))
