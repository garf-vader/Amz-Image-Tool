import re
import sys
from pathlib import Path

# Match PT + 1–3 digits with optional separators/casing, e.g.:
# PT2, pt 02, PT-15, IMG_PT_07_v2
PT_PATTERN = re.compile(r'(?i)\bpt[\s._-]*(\d{1,3})\b')

# Match MAIN with optional separators/casing, e.g.:
# MAIN, main, IMG-MAIN_v2
MAIN_PATTERN = re.compile(r'(?i)\bmain\b')


def extract_tag(stem: str) -> str | None:
    """Extract PTxx or MAIN tag from filename stem."""
    # Check for PTxx
    m = PT_PATTERN.search(stem)
    if m:
        n = int(m.group(1))
        return f"PT{n % 100:02d}"

    # Check for MAIN
    if MAIN_PATTERN.search(stem):
        return "MAIN"

    return None


def main():
    # Usage:
    #   python rename_pt_only.py [--dry-run] [root_dir]
    args = sys.argv[1:]
    dry_run = False
    if args and args[0] == "--dry-run":
        dry_run = True
        args = args[1:]
    root = Path(args[0]).resolve() if args else Path.cwd()

    total, skipped, conflicts = 0, 0, 0
    for f in root.rglob("*"):
        if not f.is_file():
            continue

        tag = extract_tag(f.stem)
        if not tag:
            skipped += 1
            continue

        ext = f.suffix.lower() if f.suffix else ".jpg"
        new_name = f"{tag}{ext}"
        target = f.with_name(new_name)

        if f.name == new_name:
            continue
        if target.exists():
            print(f"⚠️  Skipping (target exists): {target}")
            conflicts += 1
            continue

        if dry_run:
            print(f"Would rename: {f} -> {new_name}")
        else:
            f.rename(target)
            print(f"Renamed: {f} -> {new_name}")
        total += 1

    print(
        f"\n🎯 {'Would rename' if dry_run else 'Total files renamed'}: {total} | "
        f"Skipped (no PTxx/MAIN): {skipped} | Conflicts: {conflicts}\n"
    )


if __name__ == "__main__":
    main()
