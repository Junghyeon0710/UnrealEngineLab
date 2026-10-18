"""Copy the Game Animation Sample assets the parkour course needs into this project's Content.

gasp_packages.txt lists every /Game package that SandboxCharacter_Mover, PC_Sandbox, IMC_Sandbox and the
level prototyping blocks hard-reference in GameAnimationSample (UE 5.8). Packages keep their original
paths, the same as the editor's Migrate, so references keep working without redirectors.

Run with the UnrealEngineLab editor closed:
    python Scripts/ParkourCourse/import_gasp_assets.py "D:/Unreal Projects/GameAnimationSample"
"""
from pathlib import Path
import filecmp
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
LIST = Path(__file__).with_name("gasp_packages.txt")
SUFFIXES = (".uasset", ".umap", ".ubulk", ".uexp", ".uptnl")


def package_files(content, package):
    base = content / package[len("/Game/"):]
    return [p for p in base.parent.glob(base.name + ".*") if p.suffix in SUFFIXES]


def main(sample_root):
    source = Path(sample_root) / "Content"
    target = ROOT / "Content"
    packages = [line.strip() for line in LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    plan, missing, conflicts = [], [], []
    for package in packages:
        files = package_files(source, package)
        if not files:
            missing.append(package)
        for f in files:
            dest = target / f.relative_to(source)
            if dest.exists() and not filecmp.cmp(f, dest, shallow=False):
                conflicts.append(str(dest))
            plan.append((f, dest))
    if missing or conflicts:
        print("missing in the sample:", missing[:20])
        print("different file already in this project:", conflicts[:20])
        sys.exit(1)
    copied = 0
    for f, dest in plan:
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            copied += 1
    print(f"{len(packages)} packages, {len(plan)} files, {copied} copied, "
          f"{sum(f.stat().st_size for f, _ in plan) / 1e6:.0f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "D:/Unreal Projects/GameAnimationSample")
