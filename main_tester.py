#!/usr/bin/env python3
"""
Debug helper: copy model/producttype/colour.jpg -> model/producttype/colour/MAIN.jpg
"""

import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox


def _sort_front_images(root_dir: str):
    """
    Ask user for a folder of front images.
    For each model/producttype/colour.jpg, copy it into model/producttype/colour/MAIN.jpg.
    """
    path = filedialog.askdirectory(title="Choose FRONT IMAGES folder")
    if not path:
        print("No FRONT IMAGES folder chosen.")
        return

    copied = 0
    skipped = 0

    for dirpath, _, files in os.walk(path):
        for fname in files:
            name, ext = os.path.splitext(fname)
            if ext.lower() != ".jpg":
                continue

            colour = name.strip()
            rel = os.path.relpath(dirpath, path).replace("\\", "/").strip("/")
            # rel should now be model/producttype
            target_dir = os.path.join(root_dir, rel, colour)

            if not os.path.isdir(target_dir):
                print(f"⚠ Skipped: {target_dir} not found")
                skipped += 1
                continue

            src = os.path.join(dirpath, fname)
            dst = os.path.join(target_dir, "MAIN.jpg")

            try:
                shutil.copy2(src, dst)
                print(f"✓ Copied {src} → {dst}")
                copied += 1
            except Exception as e:
                print(f"✗ Failed {src}: {e}")
                skipped += 1

    print(f"\nDone. Copied: {copied}, Skipped: {skipped}")
    try:
        messagebox.showinfo("Front Images", f"Copied: {copied}, Skipped: {skipped}")
    except Exception:
        pass


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()  # Hide main window

    root_dir = filedialog.askdirectory(title="Choose ROOT folder (models/producttypes)")
    if not root_dir:
        print("No ROOT folder chosen.")
    else:
        _sort_front_images(root_dir)
