#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from ui_utils import get_executable_dir

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
ASIN_RE = re.compile(r"^[A-Z0-9]{10}$", re.IGNORECASE)


def _sanitize(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    return re.sub(r"\s+", " ", name).strip()


def _load_sku2asin_csv() -> dict[str, str]:
    path = Path.cwd() / "sku2asin.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing sku2asin.csv in {Path.cwd()}")

    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError("sku2asin.csv missing header row")

        cols = {c.lower(): c for c in reader.fieldnames}
        if "sku" not in cols or "asin" not in cols:
            raise ValueError("sku2asin.csv must have 'sku' and 'asin' columns")

        sku_col, asin_col = cols["sku"], cols["asin"]
        mapping: dict[str, str] = {}
        for row in reader:
            sku = (row.get(sku_col) or "").strip().lower()
            asin = (row.get(asin_col) or "").strip().upper()
            if sku and ASIN_RE.match(asin):
                mapping[sku] = asin
        return mapping


def _derive_sku(file_path: Path, root: Path) -> str:
    parts = list(file_path.relative_to(root).parts[:-1])
    parts = (parts + [""] * 4)[-4:]
    return _sanitize(" ".join(parts))


def _extract_variant(file_name: str, fallback_ext: str) -> tuple[str, str] | None:
    m = re.match(r"^(.+?)\.(MAIN|PT\d{2})\.(.+)$", file_name, re.IGNORECASE)
    if m:
        return m.group(2).upper(), m.group(3)
    m = re.match(r"^(PT\d{2})\.(.+)$", file_name, re.IGNORECASE)
    if m:
        return m.group(1).upper(), m.group(2)
    if re.match(r"^MAIN\.(.+)$", file_name, re.IGNORECASE):
        return "MAIN", fallback_ext
    return None


def _build_output_root(input_root: Path) -> Path:
    timestamp = input_root.name if input_root.parent.name == "Outputs" else datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(get_executable_dir()) / "Outputs" / f"{timestamp}_Renamed"
    out.mkdir(parents=True, exist_ok=True)
    return out


def create_zip_archives(output_root: Path, max_zip_size: int = 1 * 1024 * 1024 * 1024) -> None:
    files: list[tuple[Path, int]] = []
    for file_path in output_root.rglob("*"):
        if file_path.is_file():
            try:
                files.append((file_path, file_path.stat().st_size))
            except OSError:
                pass

    if not files:
        print("No files to zip.")
        return

    files.sort(key=lambda item: item[1], reverse=True)
    bins: list[list[tuple[Path, int]]] = []
    bin_sizes: list[int] = []

    for file_path, size in files:
        for idx, current in enumerate(bin_sizes):
            if current + size <= max_zip_size:
                bins[idx].append((file_path, size))
                bin_sizes[idx] += size
                break
        else:
            bins.append([(file_path, size)])
            bin_sizes.append(size)

    timestamp = output_root.name.replace("_Renamed", "")
    for idx, group in enumerate(bins, start=1):
        zip_path = output_root.parent / f"{timestamp}_part{idx}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path, _ in group:
                zf.write(file_path, file_path.relative_to(output_root))
        print(f"✓ Created: {zip_path}")


def process_root(root: str | Path) -> str:
    root_path = Path(root)
    if not root_path.is_absolute():
        root_path = Path.cwd() / root_path
    if not root_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {root_path}")

    try:
        sku2asin = _load_sku2asin_csv()
    except Exception as exc:
        print(f"⚠️  {exc}")
        return ""

    output_root = _build_output_root(root_path)
    copied = 0

    for file_path in root_path.rglob("*"):
        if not (file_path.is_file() and file_path.suffix.lower() in IMAGE_EXTS):
            continue

        variant_info = _extract_variant(file_path.name, file_path.suffix.lstrip("."))
        if not variant_info:
            continue
        variant, ext = variant_info

        sku = _derive_sku(file_path, root_path).lower()
        asin = sku2asin.get(sku) or sku2asin.get(sku.replace("-", "/"))
        if not asin:
            continue

        rel_parent = file_path.relative_to(root_path).parent
        target = output_root / rel_parent / f"{asin}.{variant}.{ext}"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, target)
        copied += 1

    print(f"🎯 Finished. Total files copied: {copied}")
    if copied:
        create_zip_archives(output_root)
    return str(output_root)


run = process_root


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python amz_rename.py <root>")
        sys.exit(1)
    try:
        process_root(sys.argv[1])
    except Exception as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
