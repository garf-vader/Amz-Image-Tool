import os
import sys
import shutil
import tkinter as tk
from tkinter import messagebox
from typing import List

from ui_utils import (
    IMAGE_EXTS,
    ROW_PAD_Y,
    natural_key,
    pastel_for_name,
    ThumbItem,
    find_leaf_dirs,
)

from ui_utils import get_output_root

# ====================== Phase A: Colour Planner ======================
class ColorPhase(tk.Frame):
    def __init__(self, master, root_dir, on_complete, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.on_complete = on_complete

        # Accumulate in-memory colour map (relative POSIX paths -> list[str]).
        self.col_map: dict[str, list[str]] = {}

        self.top_dir = root_dir
        self.dir_path = ""       # current leaf
        self.leaf_dirs: List[str] = find_leaf_dirs(root_dir)
        self.leaf_idx = 0
        self.items: list[ThumbItem] = []
        self.row_widgets: list[tk.Frame] = []
        self.duplicate_all_vars: list[tk.BooleanVar] = []  # Track which images are "duplicate for all"
        self.duplicate_indices: dict[str, list[int]] = {}  # Store duplicate indices per leaf path

        # --- Top bar ---
        top = tk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        tk.Label(top, text="Please enter Colour sequence", font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
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

        self.output_root = get_output_root(root_dir)
        if not self.leaf_dirs:
            messagebox.showinfo("No leaf folders", "No leaf folders with images were found.")
            self.btn_next.config(state=tk.DISABLED)
        else:
            self._load_leaf(0)
            self._update_label()

    # ---- Root / Leaves ----

    # pick_root removed; folder is chosen in start menu and passed in



    def _load_leaf(self, idx: int):
        self.leaf_idx = idx
        self.dir_path = self.leaf_dirs[idx]
        names = sorted([f for f in os.listdir(self.dir_path) 
                       if os.path.splitext(f)[1].lower() in IMAGE_EXTS], key=natural_key)
        self.items = [ThumbItem(os.path.join(self.dir_path, f), i) for i, f in enumerate(names)]
        self.apply_colors()
        self.btn_next.config(state=tk.NORMAL)
        self._copy_to_output()

    def _copy_to_output(self):
        # Legacy method - now handled by colour_sorter with duplicate logic
        rel_path = os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/")
        output_leaf_dir = os.path.join(self.output_root, rel_path)
        os.makedirs(output_leaf_dir, exist_ok=True)
        for item in self.items:
            shutil.copy2(item.path, output_leaf_dir)

    def _last_two_dirs(self, path):
        parts = os.path.normpath(path).split(os.sep)
        return os.sep.join(parts[-2:]) if len(parts) >= 2 else path

    def _update_label(self):
        short_path = self._last_two_dirs(self.dir_path)
        if self.leaf_dirs:
            self.lbl_dir.config(text=f"[{self.leaf_idx+1}/{len(self.leaf_dirs)}] {short_path}")
        else:
            self.lbl_dir.config(text=short_path or "No folder selected")

    def _rebuild_entries(self):
        for w in self.colors_frame.winfo_children():
            w.destroy()
        self.color_entries.clear()
        for i in range(max(1, min(self.num_colors.get(), 20))):
            row = tk.Frame(self.colors_frame)
            row.pack(side=tk.LEFT, padx=(0, 10))
            tk.Label(row, text=f"{i+1}.").pack(anchor="w")
            e = tk.Entry(row, width=14)
            e.pack(anchor="w")
            self.color_entries.append(e)

    def _suggest_defaults(self, names: list[str]):
        for i, name in enumerate(names[:len(self.color_entries)]):
            self.color_entries[i].insert(0, name)

    def _get_sequence(self) -> list[str]:
        return [e.get().strip() for e in self.color_entries if e.get().strip()]

    def apply_colors(self):
        cols = self._get_sequence()
        if not cols:
            for it in self.items:
                it.assigned_color = ""
            self._render_list()
            return
        
        # Build list of indices that are NOT marked for duplication
        normal_indices = []
        for idx in range(len(self.items)):
            if idx < len(self.duplicate_all_vars) and not self.duplicate_all_vars[idx].get():
                normal_indices.append(idx)
        
        # Assign colors to normal (non-duplicate) items using round-robin
        for i, idx in enumerate(normal_indices):
            self.items[idx].assigned_color = cols[i % len(cols)]
        
        # Mark duplicate items with a dash
        for idx in range(len(self.items)):
            if idx < len(self.duplicate_all_vars) and self.duplicate_all_vars[idx].get():
                self.items[idx].assigned_color = "—"
        
        self._render_list()

    def _create_item_row(self, idx, item):
        row = tk.Frame(self.list_frame, bd=1, relief=tk.SOLID, background="#fff")
        thumb = item.load_thumb()
        img = tk.Label(row, image=thumb, bd=0)
        img.image = thumb
        img.pack(side=tk.LEFT, padx=8, pady=8)
        
        meta = tk.Frame(row, background="#fff")
        meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        tk.Label(meta, text=f"#{idx}", font=("TkDefaultFont", 10, "bold"), background="#fff").pack(anchor="w")
        
        cname = item.assigned_color or "—"
        badge_bg = pastel_for_name(cname) if item.assigned_color else "#eee"
        tk.Label(meta, text=f"  {cname}  ", bg=badge_bg, bd=1, relief=tk.SOLID).pack(anchor="w")
        tk.Label(meta, text=os.path.basename(item.path), background="#fff").pack(anchor="w")
        
        # Add checkbox for "duplicate to all colors"
        dup_var = tk.BooleanVar(value=False)
        self.duplicate_all_vars.append(dup_var)
        chk = tk.Checkbutton(meta, text="Duplicate to all colors", variable=dup_var, 
                            background="#fff", command=lambda: self._on_duplicate_toggle(idx))
        chk.pack(anchor="w")
        
        for w in (row, img, meta):
            w.bindtags(("Wheel",) + w.bindtags())
        return row

    def _render_list(self):
        # Save current checkbox states before destroying widgets
        saved_states = [var.get() for var in self.duplicate_all_vars]
        
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.row_widgets = []
        self.duplicate_all_vars = []  # Reset duplicate tracking
        
        for idx, item in enumerate(self.items):
            row = self._create_item_row(idx, item)
            row.pack(fill=tk.X, padx=4, pady=ROW_PAD_Y)
            self.row_widgets.append(row)
            # Restore saved state if available
            if idx < len(saved_states):
                self.duplicate_all_vars[idx].set(saved_states[idx])
        
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_duplicate_toggle(self, idx):
        """Called when duplicate checkbox is toggled - update color assignments."""
        self.apply_colors()

    def _remember_current_leaf_colors(self):
        if not (self.top_dir and self.dir_path):
            return
        rel = os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/").strip("/")
        seq = self._get_sequence()
        if seq:
            self.col_map[rel] = seq
        elif rel in self.col_map:
            self.col_map.pop(rel, None)
        
        # Store which images are marked for duplication to all colors
        dup_indices = []
        for idx, var in enumerate(self.duplicate_all_vars):
            if var.get():
                dup_indices.append(idx)
        if dup_indices:
            self.duplicate_indices[rel] = dup_indices
        elif rel in self.duplicate_indices:
            self.duplicate_indices.pop(rel, None)

    def next_model(self):
        if not self.items:
            return
        self._remember_current_leaf_colors()
        nxt = self.leaf_idx + 1
        if nxt >= len(self.leaf_dirs):
            self._complete_batch()
            return
        self._load_leaf(nxt)
        self._update_label()

    def _complete_batch(self):
        messagebox.showinfo("Batch complete", "Recorded colour sequences for all leaf folders.")
        try:
            import colour_sorter
            colour_output = colour_sorter.run_with_map(
                self.top_dir, 
                self.col_map, 
                apply_changes=True,
                duplicate_indices=self.duplicate_indices
            )
        except Exception as e:
            messagebox.showerror("colour_sorter failed", str(e))
            colour_output = self.top_dir
        if callable(self.on_complete):
            self.on_complete(colour_output)

    def _on_mousewheel(self, event):
        step = -1 if (event.delta > 0 and sys.platform=="darwin") else -int(event.delta/120) if event.delta else 1
        if step: self.canvas.yview_scroll(step,"units")