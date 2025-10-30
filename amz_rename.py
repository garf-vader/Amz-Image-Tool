#!/usr/bin/env python3
"""
amz_rename.py

Runs Amazon image renaming logic within the current working directory.

Usage:
  python amz_rename.py <root>

Behavior:
  - Looks for 'sku2asin.csv' in the current working directory.
  - Operates on the <root> subdirectory inside the current working directory.
  - Ignores where this script physically resides.
"""
from __future__ import annotations
import sys, re, os, csv
from pathlib import Path


def _load_sku2asin_csv(ASIN_RE) -> dict[str, str]:
    """Load sku2asin.csv (must be in current working directory)."""
    path = Path.cwd() / "sku2asin.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing sku2asin.csv in {Path.cwd()}")
    mapping: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError("sku2asin.csv missing header row.")
        headers = {h.lower(): h for h in r.fieldnames}
        if "sku" not in headers or "asin" not in headers:
            raise ValueError("sku2asin.csv must have 'sku' and 'asin' columns.")
        sku_col, asin_col = headers["sku"], headers["asin"]
        for row in r:
            sku = (row.get(sku_col) or "").strip().lower()
            asin = (row.get(asin_col) or "").strip().upper()
            if sku and ASIN_RE.match(asin):
                mapping[sku] = asin
    return mapping


def sanitize_for_windows(name: str) -> str:
    INVALID_WIN_CHARS = r'<>:"/\\|?*'
    name = re.sub(f"[{re.escape(INVALID_WIN_CHARS)}]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def should_rename(file_path: Path) -> bool:
    EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    return file_path.is_file() and file_path.suffix.lower() in EXTENSIONS


def rename_in_place(file_path: Path, sku: str) -> bool:
    stem, ext = file_path.stem, file_path.suffix
    new_name = sanitize_for_windows(f"{sku}.{stem}{ext}")
    if file_path.name == new_name:
        return False
    target = file_path.with_name(new_name)
    if target.exists():
        print(f"⚠️  Skipping (target exists): {target}")
        return False
    os.replace(file_path, target)
    print(f"Renamed: {file_path.name} -> {new_name}")
    return True


def derive_sku_from_file(file_path: Path, root: Path) -> str:
    # Get the 4 folders up from the file (excluding the file itself)
    rel_parts = list(file_path.relative_to(root).parts[:-1])
    # Always use exactly 4 parts, pad with empty strings if needed
    if len(rel_parts) < 4:
        sku_parts = rel_parts + [''] * (4 - len(rel_parts))
    else:
        sku_parts = rel_parts[-4:]
    return sanitize_for_windows(" ".join(sku_parts))


def sku2asin_rename(root: Path) -> int:
    """Second pass: rename 'SKU.VARIANT.ext' -> 'ASIN.VARIANT.ext' using sku2asin.csv."""
    NAME_RE = re.compile(r"^(.+?)\.(MAIN|PT\d{2})\.(.+)$", re.IGNORECASE)
    ASIN_RE = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)

    try:
        sku2asin = _load_sku2asin_csv(ASIN_RE)
    except Exception as e:
        print(f"⚠️  {e}")
        return 0

    renamed = 0
    for f in root.rglob("*"):
        if not f.is_file():
            continue

        m = NAME_RE.match(f.name)
        if not m:
            continue

        current_id, variant, ext = m.group(1).lower(), m.group(2).upper(), m.group(3)

        # Skip if already ASIN
        if ASIN_RE.match(current_id):
            continue

        # Look up ASIN by SKU
        asin = sku2asin.get(current_id)
        if not asin:
            alt_key = current_id.replace("-", "/")
            asin = sku2asin.get(alt_key)

        if not asin:
            # Nothing found in mapping
            continue

        new_name = f"{asin}.{variant}.{ext}"
        target = f.with_name(new_name)
        if target.exists():
            print(f"⚠️  Skipping (target exists): {target.name}")
            continue

        os.replace(f, target)
        print(f"Renamed (ASIN): {f.name} -> {new_name}")
        renamed += 1

    return renamed



def process_root(root: str | Path) -> int:
    """Walk all files under *root* (relative to CWD) and rename them."""
    root_path = Path.cwd() / root
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    # Create timestamped output folder
    import os
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_dir = Path(os.path.dirname(__file__))
    output_root = script_dir / "Outputs" / timestamp
    output_root.mkdir(parents=True, exist_ok=True)

    total = 0
    # Load ASIN mapping once
    NAME_RE = re.compile(r"^(.+?)\.(MAIN|PT\d{2})\.(.+)$", re.IGNORECASE)
    ASIN_RE = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)
    try:
        sku2asin = _load_sku2asin_csv(ASIN_RE)
    except Exception as e:
        print(f"⚠️  {e}")
        return 0

    for file_path in root_path.rglob("*"):
        if not should_rename(file_path):
            continue
        sku = derive_sku_from_file(file_path, root_path)
        if not sku:
            print(f"⚠️  Could not derive SKU for: {file_path}")
            continue
        # Determine variant from filename
        m = NAME_RE.match(file_path.name)
        if m:
            variant = m.group(2).upper()
            ext = m.group(3)
        else:
            # Try to match PTxx.jpg pattern (no SKU prefix)
            pt_match = re.match(r"^(PT\d{2})\.(.+)$", file_path.name, re.IGNORECASE)
            if pt_match:
                variant = pt_match.group(1).upper()
                ext = pt_match.group(2)
            else:
                print(f"⚠️  Could not parse variant for: {file_path.name}")
                continue
        # Lookup ASIN
        asin = sku2asin.get(sku.lower())
        if not asin:
            alt_key = sku.lower().replace("-", "/")
            asin = sku2asin.get(alt_key)
        if not asin:
            print(f"⚠️  No ASIN found for SKU: {sku}")
            continue
        target_name = f"{asin}.{variant}.{ext}"
        rel_path = file_path.relative_to(root_path)
        target_path = output_root / rel_path.parent / target_name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(file_path, target_path)
        print(f"Copied: {file_path} -> {target_path}")
        total += 1
    print(f"🎯 Finished. Total files copied: {total}")
    return str(output_root)


run = process_root


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python amz_rename.py <root>")
        sys.exit(1)
    try:
        process_root(sys.argv[1])
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
