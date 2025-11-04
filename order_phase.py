import json
import os
from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QHBoxLayout,
    QMessageBox,
    QAbstractItemView,
)

from ui_utils import (
    IMAGE_EXTS,
    ROW_PAD_Y,
    TARGET_FOLDER_NAMES,
    ThumbItem,
    natural_key,
)


class ItemRowWidget(QWidget):
    """List row representing a single thumbnail entry."""

    def __init__(self, item: ThumbItem, index: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.item = item

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        thumb = item.load_thumb()
        self.image = QLabel()
        self.image.setPixmap(thumb)
        self.image.setAlignment(Qt.AlignCenter)
        self.image.setFixedSize(thumb.size())
        layout.addWidget(self.image)

        meta = QWidget()
        meta_layout = QVBoxLayout(meta)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(6)

        self.index_label = QLabel()
        font = QFont()
        font.setBold(True)
        self.index_label.setFont(font)
        meta_layout.addWidget(self.index_label)

        meta_layout.addWidget(QLabel(f"orig: {item.orig_index} • {os.path.basename(item.path)}"))
        meta_layout.addStretch(1)

        layout.addWidget(meta, stretch=1)
        self.update_index(index)

    def update_index(self, idx: int) -> None:
        self.index_label.setText(f"#{idx}")


class ReorderListWidget(QListWidget):
    orderChanged = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(ROW_PAD_Y)

    def dropEvent(self, event):  # type: ignore[override]
        super().dropEvent(event)
        self.orderChanged.emit()


class OrderPhase(QWidget):
    """PyQt implementation of the reorder/drag-drop phase."""

    def __init__(self, root_dir: str, on_complete=None, parent: QWidget | None = None):
        super().__init__(parent)
        self.on_complete = on_complete
        self.root_dir = root_dir

        self.pt_map: dict[str, list[int]] = {}

        self.dir_path = ""
        self.items: list[ThumbItem] = []

        self.vw_queue: List[str] = []
        self.vw_idx: int = -1

        self._build_ui()
        self._start_queue_from_root(root_dir)

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Top bar
        top_bar = QHBoxLayout()
        title = QLabel("Please place the images in the correct order")
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        top_bar.addWidget(title)

        self.lbl_dir = QLabel("No folder selected")
        self.lbl_dir.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        top_bar.addWidget(self.lbl_dir, stretch=1)

        self.btn_next = QPushButton("Next Model (Confirm)")
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self.next_model_confirm)
        top_bar.addWidget(self.btn_next)

        layout.addLayout(top_bar)

        self.list_widget = ReorderListWidget()
        self.list_widget.orderChanged.connect(self._on_order_changed)
        layout.addWidget(self.list_widget, stretch=1)

        bottom = QHBoxLayout()
        self.status = QLabel("")
        bottom.addWidget(self.status, stretch=1)
        layout.addLayout(bottom)

    # ------------------------------------------------------------------
    def _start_queue_from_root(self, root: str) -> None:
        self.vw_queue = self._find_case_leafs(root)
        if not self.vw_queue:
            QMessageBox.information(self, "Not found", f"No '{TARGET_FOLDER_NAMES}' folders found under:\n{root}")
            self.btn_next.setEnabled(False)
            return
        self.vw_idx = 0
        self.btn_next.setEnabled(True)
        self._load_current()
        self._update_progress_label()

    def _find_case_leafs(self, root: str) -> List[str]:
        found: List[str] = []
        for dirpath, _dirnames, _filenames in os.walk(root):
            if os.path.basename(dirpath) in TARGET_FOLDER_NAMES:
                leaf = self._first_leaf_dir(dirpath)
                if leaf and self._has_images(leaf):
                    found.append(os.path.normpath(leaf))
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

    def _load_current(self) -> None:
        path = self.vw_queue[self.vw_idx]
        self.dir_path = path
        files = sorted(
            [f for f in os.listdir(path) if os.path.splitext(f)[1].lower() in IMAGE_EXTS],
            key=natural_key,
        )
        self.items = [ThumbItem(os.path.join(path, f), i) for i, f in enumerate(files)]
        self._render_list()
        self.status.setText(f"Loaded {len(self.items)} images")

    def _render_list(self) -> None:
        self.list_widget.clear()
        for idx, item in enumerate(self.items):
            widget = ItemRowWidget(item, idx)
            list_item = QListWidgetItem()
            list_item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)

    def _mapping_original_to_desired(self) -> list[int]:
        inv = [None] * len(self.items)
        for new_pos, it in enumerate(self.items):
            inv[it.orig_index] = new_pos
        if any(i is None for i in inv):
            raise ValueError("Invalid mapping: None value encountered in mapping. This indicates a bug in the mapping logic or input data.")
        return inv

    def _remember_current_leaf_mapping(self) -> None:
        if not (self.root_dir and self.dir_path and self.items):
            return
        rel_leaf = os.path.relpath(self.dir_path, self.root_dir).replace("\\", "/").strip("/")
        base_rel = os.path.dirname(rel_leaf)
        self.pt_map[base_rel] = self._mapping_original_to_desired()

    def _update_progress_label(self) -> None:
        if self.vw_queue and 0 <= self.vw_idx < len(self.vw_queue):
            self.lbl_dir.setText(f"[{self.vw_idx + 1}/{len(self.vw_queue)}] {self.dir_path}")
        else:
            self.lbl_dir.setText(self.dir_path or "No folder selected")

    def _on_order_changed(self) -> None:
        new_items: list[ThumbItem] = []
        for row in range(self.list_widget.count()):
            list_item = self.list_widget.item(row)
            widget = self.list_widget.itemWidget(list_item)
            if isinstance(widget, ItemRowWidget):
                widget.update_index(row)
                new_items.append(widget.item)
        self.items = new_items
        self.status.setText("Reordered items")

    def next_model_confirm(self) -> None:
        self._remember_current_leaf_mapping()
        self.vw_idx += 1
        if self.vw_idx >= len(self.vw_queue):
            self._complete_batch()
            return
        self._load_current()
        self._update_progress_label()

    def _complete_batch(self) -> None:
        self.btn_next.setEnabled(False)
        self.status.setText("All VintageWallet models processed.")
        QMessageBox.information(self, "Done", "All VintageWallet models processed.")

        pt_output = self.root_dir
        try:
            import pt_order

            pt_output = pt_order.run_with_map(self.root_dir, self.pt_map, apply_changes=True)
        except Exception as exc:  # pragma: no cover - defensive
            print("pt_order failed:", exc)

        if callable(self.on_complete):
            self.on_complete(pt_output)
