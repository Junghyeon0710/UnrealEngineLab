"""Summarise the steady-state window of AnimBudget measurement CSVs.

Files are matched to labels by modification time, so pass the labels in the
same order the runs happened:

    python Scripts/AnimBudget/analyze.py baseline budget1 budget2
"""
import csv, glob, os, statistics, sys

csv.field_size_limit(10 * 1024 * 1024)

CSVDIR = os.environ.get(
    "ANIMBUDGET_CSV_DIR",
    os.path.expandvars(r"$LOCALAPPDATA/UnrealEngine/5.8/Saved/Profiling/CSV"),
)
COLS = [
    ("FrameTime", "frame_ms"),
    ("GameThreadTime", "gt_ms"),
    ("AnimationBudget/GameThread/BudgetedAnimation", "anim_ms"),
    ("Exclusive/GameThread/AnimationBudgetAllocator", "alloc_ms"),
    ("AnimationBudget/AverageWorkUnitTimeMs", "workunit_ms"),
    ("AnimBudgetTest/NumPoseTicked", "poseticked"),
    ("AnimBudgetTest/AnimQuality", "quality"),
    ("AnimBudgetTest/NumReducedWork", "reduced"),
    ("AnimBudgetTest/NumInterpolating", "interp"),
    ("AnimBudgetTest/AvgTickRate", "tickrate"),
]
WINDOW = 400  # steady-state frames taken from the end of the capture


def summarize(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.DictReader(fh))
    rows = [r for r in rows if r.get("FrameTime")]
    rows = rows[-WINDOW:]
    out = {"frames": len(rows)}
    for col, key in COLS:
        vals = []
        for r in rows:
            try:
                vals.append(float(r[col]))
            except (TypeError, ValueError, KeyError):
                pass
        out[key] = statistics.median(vals) if vals else float("nan")
    out["fps"] = 1000.0 / out["frame_ms"] if out["frame_ms"] else float("nan")
    return out


def main():
    labels = sys.argv[1:]
    files = sorted(glob.glob(os.path.join(CSVDIR, "*.csv")), key=os.path.getmtime)
    if labels and len(labels) != len(files):
        print(f"warning: {len(labels)} labels for {len(files)} csv files")
    hdr = (f"{'case':<18}{'frames':>7}{'gt_ms':>9}{'anim_ms':>9}{'alloc_ms':>9}"
           f"{'ticked':>8}{'quality':>9}{'interp':>8}{'tickrate':>10}{'reduced':>9}{'fps':>7}")
    print(hdr)
    print("-" * len(hdr))
    for i, f in enumerate(files):
        s = summarize(f)
        label = labels[i] if i < len(labels) else os.path.basename(f)[:17]
        print(f"{label:<18}{s['frames']:>7}{s['gt_ms']:>9.2f}{s['anim_ms']:>9.2f}{s['alloc_ms']:>9.3f}"
              f"{s['poseticked']:>8.0f}{s['quality']:>9.3f}{s['interp']:>8.0f}{s['tickrate']:>10.2f}"
              f"{s['reduced']:>9.0f}{s['fps']:>7.1f}")


if __name__ == "__main__":
    main()
