
#!/usr/bin/env python3
"""
combined_ui.py — Combined workflow (no file I/O for maps)

1) Colour Phase:
   - User selects ROOT.
   - For each leaf with images, user sets a colour sequence.
   - We accumulate in-memory `col_map` keyed by leaf path relative to ROOT (POSIX).
   - On completion, call: colour_sorter.run_with_map(ROOT, col_map).

2) Order Phase:
   - For each 'VintageWallet' base, user reorders one representative leaf via drag & drop.
   - We accumulate in-memory `pt_map` keyed by base path (e.g., ".../VintageWallet") relative to ROOT.
   - On completion, call: pt_order.run_with_map(ROOT, pt_map). Then amz_rename(ROOT).

UI kept similar to your originals, but JSON writing is removed.
"""


import os
import sys
import importlib
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import List, Optional
from datetime import datetime

from ui_utils import (
    IMAGE_EXTS,
    INSERT_LINE_PAD,
    INSERT_LINE_HEIGHT,
    ROW_PAD_Y,
    natural_key,
    pastel_for_name,
    ThumbItem,
    find_leaf_dirs,
)

TARGET_FOLDER_NAMES = ["VintageWallet", "ShinyWallet", "VintWallet", "ShinyCase"]

def _call_optional(func_name: str, *args, **kwargs):
    try:
        ui_mod = importlib.import_module("ui_utils")
        fn = getattr(ui_mod, func_name, None)
        if callable(fn):
            return fn(*args, **kwargs)
    except Exception:
        pass
    try:
        mod = importlib.import_module(func_name)
        fn = getattr(mod, func_name, None)
        if callable(fn):
            return fn(*args, **kwargs)
        if hasattr(mod, "main") and callable(mod.main):
            return mod.main(*args, **kwargs)
    except Exception:
        pass
    return None


def get_output_root(base_dir):
    import os
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    script_dir = os.path.dirname(__file__)
    output_root = os.path.join(script_dir, "Outputs", timestamp)
    os.makedirs(output_root, exist_ok=True)
    return output_root

# ====================== Phase A: Colour Planner ======================
class ColorPhase(tk.Frame):
    def __init__(self, master, on_complete, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_complete = on_complete

        # Accumulate in-memory colour map (relative POSIX paths -> list[str]).
        self.col_map: dict[str, list[str]] = {}

        self.top_dir = ""        # chosen root
        self.dir_path = ""       # current leaf
        self.leaf_dirs: List[str] = []
        self.leaf_idx = -1
        self.items: list[ThumbItem] = []
        self.row_widgets: list[tk.Frame] = []

        # --- Top bar ---
        top = tk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        tk.Label(top, text="Please enter Colour sequence", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
        tk.Button(top, text="Open Folder…", command=self.pick_root).pack(side=tk.LEFT, padx=(10,0))
        self.lbl_dir = tk.Label(top, text="No folder selected", anchor="w")
        self.lbl_dir.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)
        self.btn_next = tk.Button(top, text="Next Model (Confirm)", command=self.next_model, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT)

        # --- Colour controls ---
        cfg = tk.LabelFrame(self, text="Colour Sequence")
        cfg.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0,10))
        tk.Label(cfg, text="Number of Colours:").pack(side=tk.LEFT, padx=(10,6))
        self.num_colors = tk.IntVar(value=3)
        tk.Spinbox(cfg, from_=1, to=20, width=4, textvariable=self.num_colors, command=self._rebuild_entries).pack(side=tk.LEFT)
        tk.Button(cfg, text="Apply Order", command=self.apply_colors).pack(side=tk.RIGHT, padx=10)
        self.colors_frame = tk.Frame(cfg); self.colors_frame.pack(side=tk.LEFT, padx=12, pady=8, fill=tk.X, expand=True)

        self.color_entries: list[tk.Entry] = []
        self._rebuild_entries()
        self._suggest_defaults(["Black","Brown","Navy"])

        # --- Scroll area ---
        wrap = tk.Frame(self); wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y); self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_frame = tk.Frame(self.canvas); self.list_window = self.canvas.create_window((0,0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.list_window, width=e.width))

        for w in (self.canvas, self.list_frame): w.bindtags(("Wheel",)+w.bindtags())
        self.bind_class("Wheel","<MouseWheel>", self._on_mousewheel)
        self.bind_class("Wheel","<Button-4>",  lambda e: self.canvas.yview_scroll(-1,"units"))
        self.bind_class("Wheel","<Button-5>",  lambda e: self.canvas.yview_scroll( 1,"units"))

        self.status = tk.Label(self, text="", anchor="w"); self.status.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0,6))

    # ---- Root / Leaves ----

    def pick_root(self):
        path = filedialog.askdirectory(title="Choose TOP-LEVEL folder")
        if not path:
            return

        # Create timestamped output folder
        self.output_root = get_output_root(path)

        # === NEW: Ask user whether to skip colour phase ===
        if messagebox.askyesno(
            "Skip Colour Phase?",
            "Have the colours already been sorted for this folder?\n\n"
            "Click 'Yes' to skip the colour-sorting phase and move directly to the next step."
        ):
            # User wants to skip straight to next phase
            if callable(self.on_complete):
                self.on_complete(path)
            return

        # Continue as normal if not skipped
        self.top_dir = path
        self.leaf_dirs = find_leaf_dirs(path)
        self.leaf_idx = 0
        if not self.leaf_dirs:
            messagebox.showinfo("No leaf folders", "No leaf folders with images were found.")
            self.btn_next.config(state=tk.DISABLED)
            return
        self._load_leaf(0)
        self._update_label()



    def _load_leaf(self, idx: int):
        self.leaf_idx = idx
        self.dir_path = self.leaf_dirs[idx]
        names = [f for f in os.listdir(self.dir_path) if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
        names.sort(key=natural_key)
        self.items = [ThumbItem(os.path.join(self.dir_path,f), i) for i,f in enumerate(names)]
        self.apply_colors(); self.btn_next.config(state=tk.NORMAL)
        # Copy images to output folder (preserving structure)
        rel_path = os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/")
        output_leaf_dir = os.path.join(self.output_root, rel_path)
        os.makedirs(output_leaf_dir, exist_ok=True)
        for item in self.items:
            shutil.copy2(item.path, output_leaf_dir)

    def _update_label(self):
        if self.leaf_dirs:
            self.lbl_dir.config(text=f"[{self.leaf_idx+1}/{len(self.leaf_dirs)}] {self.dir_path}")
        else:
            self.lbl_dir.config(text=self.dir_path or "No folder selected")

    # ---- Colour entry helpers ----
    def _rebuild_entries(self):
        for w in self.colors_frame.winfo_children(): w.destroy()
        self.color_entries.clear()
        for i in range(max(1, min(self.num_colors.get(), 20))):
            row = tk.Frame(self.colors_frame); row.pack(side=tk.LEFT, padx=(0,10))
            tk.Label(row,text=f"{i+1}.").pack(anchor="w")
            e = tk.Entry(row, width=14); e.pack(anchor="w"); self.color_entries.append(e)

    def _suggest_defaults(self, names: list[str]):
        for i, name in enumerate(names[:len(self.color_entries)]):
            self.color_entries[i].insert(0, name)

    def _get_sequence(self) -> list[str]:
        return [e.get().strip() for e in self.color_entries if e.get().strip()]

    def apply_colors(self):
        cols = self._get_sequence()
        for idx, it in enumerate(self.items):
            it.assigned_color = cols[idx % len(cols)] if cols else ""
        self._render_list()

    def _render_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        self.row_widgets = []
        for idx, item in enumerate(self.items):
            row = tk.Frame(self.list_frame, bd=1, relief=tk.SOLID, background="#fff")
            thumb = item.load_thumb()
            img = tk.Label(row, image=thumb, bd=0); img.image = thumb; img.pack(side=tk.LEFT, padx=8, pady=8)
            meta = tk.Frame(row, background="#fff"); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
            tk.Label(meta, text=f"#{idx}", font=("TkDefaultFont",10,"bold"), background="#fff").pack(anchor="w")
            cname = item.assigned_color or "—"
            badge_bg = pastel_for_name(cname) if item.assigned_color else "#eee"
            tk.Label(meta, text=f"  {cname}  ", bg=badge_bg, bd=1, relief=tk.SOLID).pack(anchor="w")
            tk.Label(meta, text=os.path.basename(item.path), background="#fff").pack(anchor="w")
            for w in (row, img, meta): w.bindtags(("Wheel",)+w.bindtags())
            row.pack(fill=tk.X, padx=4, pady=ROW_PAD_Y)
            self.row_widgets.append(row)
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _remember_current_leaf_colors(self):
        if not (self.top_dir and self.dir_path): return
        rel = os.path.relpath(self.dir_path, self.top_dir).replace("\\","/").strip("/")
        seq = self._get_sequence()
        if seq: self.col_map[rel] = seq
        elif rel in self.col_map: self.col_map.pop(rel, None)

    def next_model(self):
        if not self.items: return
        self._remember_current_leaf_colors()
        nxt = self.leaf_idx + 1
        if nxt >= len(self.leaf_dirs):
            messagebox.showinfo("Batch complete","Recorded colour sequences for all leaf folders.")
            try:
                import colour_sorter
                colour_sorter.run_with_map(self.top_dir, self.col_map, apply_changes=True)
            except Exception as e:
                messagebox.showerror("colour_sorter failed", str(e))
            if callable(self.on_complete): self.on_complete(self.top_dir)
            return
        self._load_leaf(nxt); self._update_label()

    def _on_mousewheel(self, event):
        step = -1 if (event.delta > 0 and sys.platform=="darwin") else -int(event.delta/120) if event.delta else 1
        if step: self.canvas.yview_scroll(step,"units")


# ====================== Phase B: Order/Reorder ======================
class OrderPhase(tk.Frame):
    def __init__(self, master, root_dir: str, on_complete=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_complete = on_complete
        self.root_dir = root_dir

        # Accumulate in-memory PT mapping for all bases
        self.pt_map: dict[str, list[int]] = {}

        self.dir_path = ""
        self.items: list[ThumbItem] = []
        self.row_widgets: list[tk.Frame] = []

        self.drag_idx: Optional[int] = None
        self.insert_idx: Optional[int] = None
        self.insert_line_widget = None
        self.vw_queue: List[str] = []
        self.vw_idx: int = -1

        # --- Top bar ---
        top = tk.Frame(self); top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        tk.Label(top, text="Please place the images in the correct order", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
        self.btn_next = tk.Button(top, text="Next Model (Confirm)", command=self.next_model_confirm, state=tk.DISABLED); self.btn_next.pack(side=tk.RIGHT)
        tk.Button(top, text="Pick Root Folder", state=tk.DISABLED, command=lambda: messagebox.showinfo("Root locked","Root is set from Colour phase.")).pack(side=tk.LEFT, padx=(10,0))
        self.lbl_dir = tk.Label(top, text="No folder selected", anchor="w"); self.lbl_dir.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

        # --- Scroll area ---
        wrap = tk.Frame(self); wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y); self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_frame = tk.Frame(self.canvas); self.list_window = self.canvas.create_window((0,0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.list_window, width=e.width))

        for w in (self.canvas, self.list_frame): w.bindtags(("Wheel",)+w.bindtags())
        self.bind_class("Wheel","<MouseWheel>", self._on_mousewheel)
        self.bind_class("Wheel","<Button-4>",  lambda e: self.canvas.yview_scroll(-1,"units"))
        self.bind_class("Wheel","<Button-5>",  lambda e: self.canvas.yview_scroll( 1,"units"))

        # --- Bottom/status ---
        bottom = tk.Frame(self); bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0,10))
        tk.Button(bottom, text="Copy mapping", command=self.copy_mapping).pack(side=tk.RIGHT, padx=6)
        self.status = tk.Label(bottom, text="", anchor="w"); self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._start_queue_from_root(root_dir)

    # ---- Init / queue ----
    def _start_queue_from_root(self, root: str):
        self.vw_queue = self._find_case_leafs(root)
        if not self.vw_queue:
            messagebox.showinfo("Not found", f"No '{TARGET_FOLDER_NAMES}' folders found under:\n{root}")
            self.btn_next.config(state=tk.DISABLED); return
        self.vw_idx = 0; self.btn_next.config(state=tk.NORMAL)
        self._load_current(); self._update_progress_label()

    def _find_case_leafs(self, root: str) -> List[str]:
        found: List[str] = []
        for dirpath, dirnames, _ in os.walk(root):
            if os.path.basename(dirpath) in TARGET_FOLDER_NAMES:
                leaf = self._first_leaf_dir(dirpath)
                if leaf and self._has_images(leaf): found.append(os.path.normpath(leaf))
        seen=set(); uniq=[p for p in found if not (p in seen or seen.add(p))]
        uniq.sort(key=natural_key); return uniq

    def _first_leaf_dir(self, start: str) -> Optional[str]:
        cur = start
        while True:
            subs = [d for d in os.listdir(cur) if os.path.isdir(os.path.join(cur,d))]
            subs.sort(key=natural_key)
            if not subs: return cur
            cur = os.path.join(cur, subs[0])

    def _has_images(self, path: str) -> bool:
        try:
            return any(os.path.splitext(f)[1].lower() in IMAGE_EXTS for f in os.listdir(path))
        except FileNotFoundError:
            return False

    # ---- Load & render ----
    def _load_current(self):
        path = self.vw_queue[self.vw_idx]; self.dir_path = path
        files = [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
        files.sort(key=natural_key)
        self.items = [ThumbItem(os.path.join(path,f), i) for i,f in enumerate(files)]
        self._render_list(); self.status.config(text=f"Loaded {len(self.items)} images")

    def _render_list(self):
        for w in self.list_frame.winfo_children(): w.destroy()
        self.row_widgets = []
        for idx, item in enumerate(self.items):
            row = tk.Frame(self.list_frame, bd=1, relief=tk.SOLID, background="#fff")
            thumb = item.load_thumb()
            img = tk.Label(row, image=thumb, bd=0); img.image = thumb; img.pack(side=tk.LEFT, padx=8, pady=8)
            meta = tk.Frame(row, background="#fff"); meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
            tk.Label(meta, text=f"#{idx}", font=("TkDefaultFont",10,"bold"), background="#fff").pack(anchor="w")
            tk.Label(meta, text=f"orig: {item.orig_index} • {os.path.basename(item.path)}", background="#fff").pack(anchor="w")
            for w in (row, img, meta):
                w.bind("<Button-1>", lambda e, i=idx: self._on_press(i))
                w.bind("<B1-Motion>", self._on_motion)
                w.bind("<ButtonRelease-1>", self._on_release)
                w.bindtags(("Wheel",)+w.bindtags())
            row.pack(fill=tk.X, padx=4, pady=ROW_PAD_Y); self.row_widgets.append(row)
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    # ---- Drag & drop ----
    def _on_press(self, idx): self.drag_idx = idx; self._highlight(idx, True)
    def _on_motion(self, event):
        if self.drag_idx is None: return
        y = self.canvas.canvasy(self.winfo_pointery() - self.canvas.winfo_rooty())
        rows = [w for w in self.list_frame.winfo_children() if w is not self.insert_line_widget]
        rows.sort(key=lambda w: w.winfo_y())
        idx = 0
        for i,w in enumerate(rows):
            center = w.winfo_y() + w.winfo_height()/2
            if y < center: idx = i; break
            idx = i+1
        self.insert_idx = idx; self._show_insert_line(idx)

    def _on_release(self, event):
        if self.drag_idx is None: return
        self._highlight(self.drag_idx, False); self._clear_insert_line()
        insert_at = self.insert_idx if self.insert_idx is not None else self.drag_idx
        item = self.items.pop(self.drag_idx)
        if insert_at > self.drag_idx: insert_at -= 1
        self.items.insert(insert_at, item)
        self.drag_idx = None; self.insert_idx = None
        self._render_list(); self.status.config(text=f"Reordered → #{insert_at}")

    def _show_insert_line(self, idx: int):
        rows = [w for w in self.list_frame.winfo_children()]
        idx = max(0, min(idx, len(rows)))
        if self.insert_line_widget is None or not self.insert_line_widget.winfo_exists():
            self.insert_line_widget = tk.Frame(self.list_frame, height=INSERT_LINE_HEIGHT, bg="#1a73e8")
        try: self.insert_line_widget.pack_forget()
        except Exception: pass
        if idx < len(rows):
            try: self.insert_line_widget.pack(before=rows[idx], fill=tk.X, padx=4, pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))
            except tk.TclError: self.insert_line_widget.pack(fill=tk.X, padx=4, pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))
        else:
            self.insert_line_widget.pack(fill=tk.X, padx=4, pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))

    def _clear_insert_line(self):
        if self.insert_line_widget is not None:
            try: self.insert_line_widget.destroy()
            except Exception: pass
            self.insert_line_widget = None

    def _highlight(self, idx, on: bool):
        try: self.row_widgets[idx].configure(background="#e9f2ff" if on else "#fff")
        except Exception: pass

    # ---- Mapping & actions ----
    def _mapping_original_to_desired(self) -> list[int]:
        inv = [None]*len(self.items)
        for new_pos, it in enumerate(self.items): inv[it.orig_index] = new_pos
        return inv

    def _remember_current_leaf_mapping(self):
        """Store mapping for the current base (parent of the leaf) under a key relative to ROOT."""
        if not (self.root_dir and self.dir_path and self.items): return
        rel_leaf = os.path.relpath(self.dir_path, self.root_dir).replace("\\","/").strip("/")
        base_rel = os.path.dirname(rel_leaf)  # parent: like ".../VintageWallet"
        self.pt_map[base_rel] = self._mapping_original_to_desired()

    def copy_mapping(self):
        if not self.items: return
        import json
        self.clipboard_clear()
        self.clipboard_append(json.dumps(self._mapping_original_to_desired()))
        self.update()
        self.status.config(text="Mapping (original→new) copied to clipboard")

    def _update_progress_label(self):
        if self.vw_queue and 0 <= self.vw_idx < len(self.vw_queue):
            self.lbl_dir.config(text=f"[{self.vw_idx+1}/{len(self.vw_queue)}] {self.dir_path}")
        else:
            self.lbl_dir.config(text=self.dir_path or "No folder selected")

    def next_model_confirm(self):
        # Remember mapping for this model
        self._remember_current_leaf_mapping()

        # Advance queue
        self.vw_idx += 1
        if self.vw_idx >= len(self.vw_queue):
            self.btn_next.config(state=tk.DISABLED)
            self.status.config(text="All VintageWallet models processed.")
            messagebox.showinfo("Done","All VintageWallet models processed.")
            # Run pt_order with in-memory map, then amz_rename
            try:
                import pt_order
                pt_order.run_with_map(self.root_dir, self.pt_map, apply_changes=True)
            except Exception as e:
                print("pt_order failed:", e)
            try:
                _call_optional("amz_rename", self.root_dir)
            except Exception as e:
                print("amz_rename failed:", e)
            if callable(self.on_complete): self.on_complete()
            return
        self._load_current(); self._update_progress_label()

    def _on_mousewheel(self, event):
        step = -1 if (event.delta > 0 and sys.platform=="darwin") else -int(event.delta/120) if event.delta else 1
        if step: self.canvas.yview_scroll(step,"units")

# ====================== Front Image Sorter ======================

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



# ====================== App Orchestrator ======================
class CombinedApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Combined: Colour → Order")
        self.geometry("980x720"); self.minsize(900,620)
        self.current_phase = None; self.root_dir = None
        self._show_colour_phase()

    def _clear_phase(self):
        if self.current_phase is not None:
            self.current_phase.destroy(); self.current_phase = None

    def _show_colour_phase(self):
        self._clear_phase()
        self.current_phase = ColorPhase(self, on_complete=self._on_colour_done)
        self.current_phase.pack(fill=tk.BOTH, expand=True)

    def _on_colour_done(self, chosen_root):
        self.root_dir = chosen_root
        self._clear_phase()
        self.current_phase = OrderPhase(self, root_dir=self.root_dir, on_complete=self._on_order_done)
        self.current_phase.pack(fill=tk.BOTH, expand=True)

    def _on_order_done(self):
        try:
            if messagebox.askyesno("Front Images", "Do you want to copy front images into their folders?"):
                _sort_front_images(self.root_dir)

            if messagebox.askyesno("Amazon Rename", "Do you want to run amz_rename now?"):
                import amz_rename
                amz_rename.process_root(self.root_dir)

        finally:
            try:
                self.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    app = CombinedApp()
    app.mainloop()
