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



import tkinter as tk
from tkinter import filedialog, messagebox
from color_phase import ColorPhase
from order_phase import OrderPhase

# Helper functions for widget creation
def add_label(frame, text, fg="black", pady=5):
    lbl = tk.Label(frame, text=text, fg=fg)
    lbl.pack(pady=pady)
    return lbl

def add_button(frame, text, command, width=20, pady=5, state=tk.NORMAL):
    btn = tk.Button(frame, text=text, width=width, command=command, state=state)
    btn.pack(pady=pady)
    return btn

def add_check(frame, text, var, pady=5):
    chk = tk.Checkbutton(frame, text=text, variable=var)
    chk.pack(pady=pady)
    return chk

def run_front_images(root_dir, front_image_folder):
    if not front_image_folder:
        return
    from front_image import copy_front_images
    result = copy_front_images(front_image_folder, root_dir)
    messagebox.showinfo("Front Images", f"Copied: {result['copied']}, Skipped: {result['skipped']}")


# Minimal get_output_root for color_phase.py
def get_output_root(base_dir):
    import os
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Outputs", timestamp)
    os.makedirs(output_root, exist_ok=True)
    return output_root

class CombinedApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Image Tool Start Menu")
        self.geometry("600x600")
        self.minsize(500, 500)
        self.phase = None
        self.input_folder = None
        self.front_image_folder = None
        self._start_menu()

    def _start_menu(self):
        self._clear_phase()
        frame = tk.Frame(self)
        frame.pack(fill=tk.BOTH, expand=True, padx=40, pady=40)
        add_label(frame, "Welcome to Image Tool", fg="black", pady=10).config(font=("TkDefaultFont", 16, "bold"))
        add_button(frame, "Fetch sku2asin", self._fetch_sku2asin, width=20, pady=10)

        self.colours_sorted = tk.BooleanVar()
        add_check(frame, "Colours are already sorted", self.colours_sorted, pady=10)

        self.front_images = tk.BooleanVar()
        add_check(frame, "Copy front images into folders", self.front_images, pady=5)
        self.front_image_label = add_label(frame, "No front image folder selected", fg="red")
        self.btn_front_folder = add_button(frame, "Select Front Image Folder", self._pick_front_image_folder, width=22, pady=2, state=tk.DISABLED)
        self.front_images.trace_add('write', lambda *_: self.btn_front_folder.config(state=tk.NORMAL if self.front_images.get() else tk.DISABLED))

        self.input_label = add_label(frame, "No input folder selected", fg="red", pady=10)
        add_button(frame, "Select Input Folder", self._pick_input_folder, width=20, pady=5)

        self.amz_rename = tk.BooleanVar()
        add_check(frame, "Run amz_rename after ordering", self.amz_rename, pady=5)

        self.btn_start = add_button(frame, "Start", self._start_workflow, width=20, pady=20, state=tk.DISABLED)
        self.menu_frame = frame

    def _pick_input_folder(self):
        folder = filedialog.askdirectory(title="Choose TOP-LEVEL input folder")
        if folder:
            self.input_folder = folder
            self.input_label.config(text=f"Input: {folder.split('/')[-1]}", fg="green")
            self.btn_start.config(state=tk.NORMAL)
        else:
            self.input_folder = None
            self.input_label.config(text="No input folder selected", fg="red")
            self.btn_start.config(state=tk.DISABLED)

    def _pick_front_image_folder(self):
        folder = filedialog.askdirectory(title="Choose FRONT IMAGES folder")
        if folder:
            self.front_image_folder = folder
            self.front_image_label.config(text=f"Front Images: {folder.split('/')[-1]}", fg="green")
        else:
            self.front_image_folder = None
            self.front_image_label.config(text="No front image folder selected", fg="red")

    def _fetch_sku2asin(self):
        import subprocess, sys
        result = subprocess.run([sys.executable, "fetch_sku2asin.py"], capture_output=True, text=True)
        messagebox.showinfo("sku2asin fetch", result.stdout or "Done.")

    def _start_workflow(self):
        self.menu_frame.destroy()
        self.geometry("960x1280")
        if self.colours_sorted.get():
            self._show_phase(OrderPhase, self._on_order_done)
        else:
            self._show_phase(ColorPhase, self._on_colour_done)

    def _show_phase(self, phase_class, callback):
        self._clear_phase()
        self.phase = phase_class(self, root_dir=self.input_folder, on_complete=callback)
        self.phase.pack(fill=tk.BOTH, expand=True)

    def _on_colour_done(self, colour_output):
        self.input_folder = colour_output
        self._show_phase(OrderPhase, self._on_order_done)

    def _on_order_done(self, pt_output=None):
        if self.front_images.get() and self.front_image_folder:
            run_front_images(self.input_folder, self.front_image_folder)
        if pt_output and self.amz_rename.get():
            import amz_rename
            try:
                amz_rename.run(pt_output)
            except Exception as e:
                messagebox.showerror("amz_rename error", str(e))
        self.destroy()

    def _clear_phase(self):
        if self.phase:
            self.phase.destroy()
            self.phase = None

if __name__ == "__main__":
    CombinedApp().mainloop()
