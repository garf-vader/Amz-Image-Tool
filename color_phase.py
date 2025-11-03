import os
import shutil
from functools import partial
from typing import List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QHBoxLayout,
    QSpinBox,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from ui_utils import (
    IMAGE_EXTS,
    ROW_PAD_Y,
    natural_key,
    pastel_for_name,
    ThumbItem,
    find_leaf_dirs,
    get_output_root,
)


class ColorPhase(QWidget):
    """PyQt implementation of the colour planning phase."""

    def __init__(self, root_dir: str, on_complete, parent: QWidget | None = None):
        super().__init__(parent)
        self.on_complete = on_complete

        self.col_map: dict[str, list[str]] = {}
        self.clone_map: dict[str, str] = {}

        self.top_dir = root_dir
        self.dir_path = ""
        self.leaf_dirs: List[str] = find_leaf_dirs(root_dir)
        self.leaf_idx = 0
        self.items: list[ThumbItem] = []
        self.row_widgets: list[QFrame] = []

        self._build_ui()

        self.output_root = get_output_root(root_dir)
        if not self.leaf_dirs:
            QMessageBox.information(self, "No leaf folders", "No leaf folders with images were found.")
            self.btn_next.setEnabled(False)
        else:
            self._load_leaf(0)
            self._update_label()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("Please enter Colour sequence")
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        top_bar.addWidget(title)

        self.lbl_dir = QLabel("No folder selected")
        self.lbl_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        top_bar.addWidget(self.lbl_dir)

        self.btn_next = QPushButton("Next Model (Confirm)")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self.next_model)
        top_bar.addWidget(self.btn_next)

        layout.addLayout(top_bar)

        # Colour controls
        cfg_group = QGroupBox("Colour Sequence")
        cfg_layout = QHBoxLayout(cfg_group)
        cfg_layout.setSpacing(10)

        cfg_layout.addWidget(QLabel("Number of Colours:"))
        self.num_colors = QSpinBox()
        self.num_colors.setRange(1, 20)
        self.num_colors.setValue(3)
        self.num_colors.valueChanged.connect(self._rebuild_entries)
        cfg_layout.addWidget(self.num_colors)

        self.apply_button = QPushButton("Apply Order")
        self.apply_button.clicked.connect(self.apply_colors)
        cfg_layout.addWidget(self.apply_button, alignment=Qt.AlignRight)

        self.colors_frame = QWidget()
        self.colors_layout = QHBoxLayout(self.colors_frame)
        self.colors_layout.setContentsMargins(0, 0, 0, 0)
        self.colors_layout.setSpacing(10)
        cfg_layout.addWidget(self.colors_frame, stretch=1)

        layout.addWidget(cfg_group)

        self.color_entries: list[QLineEdit] = []
        self._rebuild_entries()
        self._suggest_defaults(["Black", "Brown", "Navy"])

        # Scroll area for thumbnails
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(ROW_PAD_Y)
        scroll_area.setWidget(self.list_container)
        layout.addWidget(scroll_area, stretch=1)

        self.status = QLabel("")
        layout.addWidget(self.status)

    # ------------------------------------------------------------------
    def _load_leaf(self, idx: int) -> None:
        self.leaf_idx = idx
        self.dir_path = self.leaf_dirs[idx]
        names = sorted(
            [f for f in os.listdir(self.dir_path) if os.path.splitext(f)[1].lower() in IMAGE_EXTS],
            key=natural_key,
        )
        self.items = [ThumbItem(os.path.join(self.dir_path, f), i) for i, f in enumerate(names)]
        self.apply_colors()
        self.btn_next.setEnabled(True)
        self._copy_to_output()
        self._refresh_status()

    def _copy_to_output(self) -> None:
        rel_path = os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/")
        output_leaf_dir = os.path.join(self.output_root, rel_path)
        os.makedirs(output_leaf_dir, exist_ok=True)
        for item in self.items:
            shutil.copy2(item.path, output_leaf_dir)

    def _last_two_dirs(self, path: str) -> str:
        parts = os.path.normpath(path).split(os.sep)
        return os.sep.join(parts[-2:]) if len(parts) >= 2 else path

    def _update_label(self) -> None:
        short_path = self._last_two_dirs(self.dir_path)
        if self.leaf_dirs:
            self.lbl_dir.setText(f"[{self.leaf_idx + 1}/{len(self.leaf_dirs)}] {short_path}")
        else:
            self.lbl_dir.setText(short_path or "No folder selected")

    def _clear_color_entries(self) -> None:
        while self.colors_layout.count():
            item = self.colors_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()

    def _rebuild_entries(self) -> None:
        self._clear_color_entries()
        self.color_entries.clear()
        count = max(1, min(self.num_colors.value(), 20))
        for idx in range(count):
            holder = QWidget()
            holder_layout = QVBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(4)
            holder_layout.addWidget(QLabel(f"{idx + 1}."))
            entry = QLineEdit()
            holder_layout.addWidget(entry)
            self.color_entries.append(entry)
            self.colors_layout.addWidget(holder)
        self.colors_layout.addStretch(1)

    def _suggest_defaults(self, names: list[str]) -> None:
        for i, name in enumerate(names[: len(self.color_entries)]):
            self.color_entries[i].setText(name)

    def _get_sequence(self) -> list[str]:
        return [entry.text().strip() for entry in self.color_entries if entry.text().strip()]

    def apply_colors(self) -> None:
        cols = self._get_sequence()
        clone_name = self._current_clone_name()
        seq_idx = 0
        for item in self.items:
            if clone_name and item.name == clone_name:
                item.assigned_color = "Clone"
            elif cols:
                item.assigned_color = cols[seq_idx % len(cols)]
                seq_idx += 1
            else:
                item.assigned_color = ""
        self._render_list()
        self._refresh_status(cols)

    def _create_item_row(self, idx: int, item: ThumbItem) -> QFrame:
        row = QFrame()
        row.setFrameShape(QFrame.StyledPanel)

        is_clone = self._current_clone_name() == item.name
        bg_colour = "#fff7e6" if is_clone else "#ffffff"
        border_colour = "#f0c36d" if is_clone else "#cccccc"
        row.setStyleSheet(f"background-color: {bg_colour}; border: 1px solid {border_colour};")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 8, 8, 8)
        row_layout.setSpacing(12)

        thumb = item.load_thumb()
        img_label = QLabel()
        img_label.setPixmap(thumb)
        img_label.setAlignment(Qt.AlignCenter)
        img_label.setFixedSize(thumb.size())
        row_layout.addWidget(img_label)

        meta = QWidget()
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        idx_label = QLabel(f"#{idx}")
        idx_font = QFont()
        idx_font.setBold(True)
        idx_label.setFont(idx_font)
        meta_layout.addWidget(idx_label)

        cname = item.assigned_color or "—"
        badge = QLabel(f"  {cname}  ")
        badge.setStyleSheet(
            f"background-color: {pastel_for_name(cname) if item.assigned_color else '#eeeeee'};"
            "border: 1px solid #999999; padding: 2px 6px;"
        )
        meta_layout.addWidget(badge)

        meta_layout.addWidget(QLabel(os.path.basename(item.path)))
        if is_clone:
            clone_note = QLabel("Clone source")
            clone_note.setStyleSheet("color: #a46900; font-style: italic;")
            meta_layout.addWidget(clone_note)
        meta_layout.addStretch(1)

        row_layout.addWidget(meta, stretch=1)
        clone_btn = QPushButton("Clone to all colours")
        clone_btn.setCheckable(True)
        clone_btn.setChecked(is_clone)
        clone_btn.clicked.connect(partial(self._handle_clone_clicked, item))
        row_layout.addWidget(clone_btn)
        return row

    def _clear_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
        self.row_widgets.clear()

    def _render_list(self) -> None:
        self._clear_list()
        for idx, item in enumerate(self.items):
            row = self._create_item_row(idx, item)
            self.list_layout.addWidget(row)
            self.row_widgets.append(row)
        self.list_layout.addStretch(1)

    def _current_rel_key(self) -> str:
        if not (self.top_dir and self.dir_path):
            return ""
        return os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/").strip("/")

    def _current_clone_name(self) -> str:
        rel = self._current_rel_key()
        return self.clone_map.get(rel, "")

    def _handle_clone_clicked(self, item: ThumbItem, checked: bool) -> None:
        if checked:
            self._set_clone_item(item)
        elif self._current_clone_name() == item.name:
            self._set_clone_item(None)
        else:
            self._refresh_status()

    def _set_clone_item(self, item: ThumbItem | None) -> None:
        rel = self._current_rel_key()
        if not rel:
            return
        if item is None:
            self.clone_map.pop(rel, None)
        else:
            self.clone_map[rel] = item.name
        self.apply_colors()

    def _refresh_status(self, cols: list[str] | None = None) -> None:
        cols = cols if cols is not None else self._get_sequence()
        parts: list[str] = []
        if not cols:
            parts.append("Enter at least one colour to assign.")
        clone_name = self._current_clone_name()
        if clone_name:
            parts.append(f"Clone image: {clone_name}")
        self.status.setText(" • ".join(parts))

    def _remember_current_leaf_colors(self) -> None:
        if not (self.top_dir and self.dir_path):
            return
        rel = os.path.relpath(self.dir_path, self.top_dir).replace("\\", "/").strip("/")
        seq = self._get_sequence()
        if seq:
            self.col_map[rel] = seq
        elif rel in self.col_map:
            self.col_map.pop(rel, None)

    def next_model(self) -> None:
        if not self.items:
            return
        self._remember_current_leaf_colors()
        nxt = self.leaf_idx + 1
        if nxt >= len(self.leaf_dirs):
            self._complete_batch()
            return
        self._load_leaf(nxt)
        self._update_label()

    def _complete_batch(self) -> None:
        QMessageBox.information(self, "Batch complete", "Recorded colour sequences for all leaf folders.")
        try:
            import colour_sorter

            colour_output = colour_sorter.run_with_map(
                self.top_dir,
                self.col_map,
                apply_changes=True,
                clone_map=self.clone_map,
            )
        except Exception as exc:  # pragma: no cover - defensive
            QMessageBox.critical(self, "colour_sorter failed", str(exc))
            colour_output = self.top_dir
        if callable(self.on_complete):
            self.on_complete(colour_output)
