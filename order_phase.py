import os
import sys
import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

from ui_utils import (
    IMAGE_EXTS,
    INSERT_LINE_PAD,
    INSERT_LINE_HEIGHT,
    ROW_PAD_Y,
    natural_key,
    ThumbItem,
    TARGET_FOLDER_NAMES,
)

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
        top = tk.Frame(self)
        top.pack(side=tk.TOP, fill=tk.X, padx=10, pady=8)
        tk.Label(top, text="Please place the images in the correct order", 
                font=("TkDefaultFont", 10, "bold")).pack(side=tk.LEFT)
        self.btn_next = tk.Button(top, text="Next Model (Confirm)", 
                                  command=self.next_model_confirm, state=tk.DISABLED)
        self.btn_next.pack(side=tk.RIGHT)
        self.lbl_dir = tk.Label(top, text="No folder selected", anchor="w")
        self.lbl_dir.pack(side=tk.LEFT, padx=12, fill=tk.X, expand=True)

        # --- Scroll area ---
        wrap = tk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.canvas = tk.Canvas(wrap, highlightthickness=0)
        scroll = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.list_frame = tk.Frame(self.canvas)
        self.list_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.list_frame.bind("<Configure>", lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.list_window, width=e.width))

        for w in (self.canvas, self.list_frame):
            w.bindtags(("Wheel",) + w.bindtags())
        self.bind_class("Wheel", "<MouseWheel>", self._on_mousewheel)
        self.bind_class("Wheel", "<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind_class("Wheel", "<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

        # --- Bottom/status ---
        bottom = tk.Frame(self)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        tk.Button(bottom, text="Copy mapping", command=self.copy_mapping).pack(side=tk.RIGHT, padx=6)
        self.status = tk.Label(bottom, text="", anchor="w")
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._start_queue_from_root(root_dir)

    def _start_queue_from_root(self, root: str):
        self.vw_queue = self._find_case_leafs(root)
        if not self.vw_queue:
            messagebox.showinfo("Not found", f"No '{TARGET_FOLDER_NAMES}' folders found under:\n{root}")
            self.btn_next.config(state=tk.DISABLED)
            return
        self.vw_idx = 0
        self.btn_next.config(state=tk.NORMAL)
        self._load_current()
        self._update_progress_label()

    def _find_case_leafs(self, root: str) -> List[str]:
        found: List[str] = []
        for dirpath, dirnames, _ in os.walk(root):
            if os.path.basename(dirpath) in TARGET_FOLDER_NAMES:
                leaf = self._first_leaf_dir(dirpath)
                if leaf and self._has_images(leaf):
                    found.append(os.path.normpath(leaf))
        # Remove duplicates while preserving order
        seen = set()
        uniq = [p for p in found if not (p in seen or seen.add(p))]
        uniq.sort(key=natural_key)
        return uniq

    def _first_leaf_dir(self, start: str) -> Optional[str]:
        cur = start
        while True:
            subs = [d for d in os.listdir(cur) if os.path.isdir(os.path.join(cur, d))]
            subs.sort(key=natural_key)
            if not subs:
                return cur
            cur = os.path.join(cur, subs[0])

    def _has_images(self, path: str) -> bool:
        try:
            return any(os.path.splitext(f)[1].lower() in IMAGE_EXTS for f in os.listdir(path))
        except FileNotFoundError:
            return False

    def _load_current(self):
        path = self.vw_queue[self.vw_idx]
        self.dir_path = path
        files = sorted([f for f in os.listdir(path) 
                       if os.path.splitext(f)[1].lower() in IMAGE_EXTS], key=natural_key)
        self.items = [ThumbItem(os.path.join(path, f), i) for i, f in enumerate(files)]
        self._render_list()
        self.status.config(text=f"Loaded {len(self.items)} images")

    def _create_item_row(self, idx, item):
        row = tk.Frame(self.list_frame, bd=1, relief=tk.SOLID, background="#fff")
        thumb = item.load_thumb()
        img = tk.Label(row, image=thumb, bd=0)
        img.image = thumb
        img.pack(side=tk.LEFT, padx=8, pady=8)
        
        meta = tk.Frame(row, background="#fff")
        meta.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        tk.Label(meta, text=f"#{idx}", font=("TkDefaultFont", 10, "bold"), background="#fff").pack(anchor="w")
        tk.Label(meta, text=f"orig: {item.orig_index} • {os.path.basename(item.path)}", background="#fff").pack(anchor="w")
        
        for w in (row, img, meta):
            w.bind("<Button-1>", lambda e, i=idx: self._on_press(i))
            w.bind("<B1-Motion>", self._on_motion)
            w.bind("<ButtonRelease-1>", self._on_release)
            w.bindtags(("Wheel",) + w.bindtags())
        return row

    def _render_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self.row_widgets = []
        for idx, item in enumerate(self.items):
            row = self._create_item_row(idx, item)
            row.pack(fill=tk.X, padx=4, pady=ROW_PAD_Y)
            self.row_widgets.append(row)
        self.list_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_press(self, idx):
        self.drag_idx = idx
        self._highlight(idx, True)
    def _on_motion(self, event):
        if self.drag_idx is None:
            return
        y = self.canvas.canvasy(self.winfo_pointery() - self.canvas.winfo_rooty())
        rows = [w for w in self.list_frame.winfo_children() if w is not self.insert_line_widget]
        rows.sort(key=lambda w: w.winfo_y())
        idx = 0
        for i, w in enumerate(rows):
            center = w.winfo_y() + w.winfo_height() / 2
            if y < center:
                idx = i
                break
            idx = i + 1
        self.insert_idx = idx
        self._show_insert_line(idx)

    def _on_release(self, event):
        if self.drag_idx is None:
            return
        self._highlight(self.drag_idx, False)
        self._clear_insert_line()
        insert_at = self.insert_idx if self.insert_idx is not None else self.drag_idx
        item = self.items.pop(self.drag_idx)
        if insert_at > self.drag_idx:
            insert_at -= 1
        self.items.insert(insert_at, item)
        self.drag_idx = None
        self.insert_idx = None
        self._render_list()
        self.status.config(text=f"Reordered → #{insert_at}")

    def _show_insert_line(self, idx: int):
        rows = [w for w in self.list_frame.winfo_children()]
        idx = max(0, min(idx, len(rows)))
        if self.insert_line_widget is None or not self.insert_line_widget.winfo_exists():
            self.insert_line_widget = tk.Frame(self.list_frame, height=INSERT_LINE_HEIGHT, bg="#1a73e8")
        try:
            self.insert_line_widget.pack_forget()
        except Exception:
            pass
        if idx < len(rows):
            try:
                self.insert_line_widget.pack(before=rows[idx], fill=tk.X, padx=4, 
                                            pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))
            except tk.TclError:
                self.insert_line_widget.pack(fill=tk.X, padx=4, 
                                            pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))
        else:
            self.insert_line_widget.pack(fill=tk.X, padx=4, 
                                        pady=(INSERT_LINE_PAD, INSERT_LINE_PAD))

    def _clear_insert_line(self):
        if self.insert_line_widget is not None:
            try:
                self.insert_line_widget.destroy()
            except Exception:
                pass
            self.insert_line_widget = None

    def _highlight(self, idx, on: bool):
        try:
            self.row_widgets[idx].configure(background="#e9f2ff" if on else "#fff")
        except Exception:
            pass

    def _mapping_original_to_desired(self) -> list[int]:
        inv = [None] * len(self.items)
        for new_pos, it in enumerate(self.items):
            inv[it.orig_index] = new_pos
        return inv

    def _remember_current_leaf_mapping(self):
        """Store mapping for the current base (parent of the leaf) under a key relative to ROOT."""
        if not (self.root_dir and self.dir_path and self.items):
            return
        rel_leaf = os.path.relpath(self.dir_path, self.root_dir).replace("\\", "/").strip("/")
        base_rel = os.path.dirname(rel_leaf)
        self.pt_map[base_rel] = self._mapping_original_to_desired()

    def copy_mapping(self):
        if not self.items:
            return
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
        self._remember_current_leaf_mapping()
        self.vw_idx += 1
        
        if self.vw_idx >= len(self.vw_queue):
            self._complete_batch()
            return
        
        self._load_current()
        self._update_progress_label()

    def _complete_batch(self):
        self.btn_next.config(state=tk.DISABLED)
        self.status.config(text="All VintageWallet models processed.")
        messagebox.showinfo("Done", "All VintageWallet models processed.")
        
        pt_output = self.root_dir
        try:
            import pt_order
            pt_output = pt_order.run_with_map(self.root_dir, self.pt_map, apply_changes=True)
        except Exception as e:
            print("pt_order failed:", e)
        
        if callable(self.on_complete):
            self.on_complete(pt_output)

    def _on_mousewheel(self, event):
        step = -1 if (event.delta > 0 and sys.platform=="darwin") else -int(event.delta/120) if event.delta else 1
        if step: self.canvas.yview_scroll(step,"units")
