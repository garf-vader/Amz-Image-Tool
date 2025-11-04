#!/usr/bin/env python3
"""Combined PyQt workflow for the colour and order phases."""

import os
import subprocess
import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QSizePolicy,
    QWidget,
)

from color_phase import ColorPhase
from order_phase import OrderPhase


def run_front_images(root_dir: str, front_image_folder: str, parent: QWidget | None = None) -> None:
    if not front_image_folder:
        return
    from front_image import copy_front_images

    result = copy_front_images(front_image_folder, root_dir)
    QMessageBox.information(
        parent,
        "Front Images",
        f"Copied: {result['copied']}, Skipped: {result['skipped']}",
    )


class CombinedApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Tool Start Menu")
        self.resize(600, 600)
        self.setMinimumSize(500, 500)

        self.phase_widget: QWidget | None = None
        self.input_folder: str | None = None
        self.front_image_folder: str | None = None
        self.fetch_completed: bool = False
        self._pending_pt_output: str | None = None
        self._copy_front_images: bool = False

        self._start_menu()

    # ------------------------------------------------------------------
    def _set_central(self, widget: QWidget) -> None:
        if old := self.centralWidget():
            old.deleteLater()
        self.setCentralWidget(widget)

    def _start_menu(self) -> None:
        menu = QWidget()
        layout = QVBoxLayout(menu)
        layout.setAlignment(Qt.AlignTop)  # type: ignore
        layout.setSpacing(12)
        layout.setContentsMargins(40, 40, 40, 40)

        title = QLabel("Welcome to Image Tool")
        font = QFont()
        font.setBold(True)
        font.setPointSize(16)
        title.setFont(font)
        layout.addWidget(title)

        self.colours_sorted_chk = QCheckBox("Colours are already sorted")
        layout.addWidget(self.colours_sorted_chk)

        self.front_images_chk = QCheckBox("Copy front images into folders")
        layout.addWidget(self.front_images_chk)

        front_row = QHBoxLayout()
        self.front_image_label = QLabel("No front image folder selected")
        self.front_image_label.setStyleSheet("color: red;")
        front_row.addWidget(self.front_image_label, stretch=1)
        self.btn_front_folder = QPushButton("Select Front Image Folder")
        self.btn_front_folder.setEnabled(False)
        self.btn_front_folder.clicked.connect(self._pick_front_image_folder)
        front_row.addWidget(self.btn_front_folder)
        layout.addLayout(front_row)

        self.front_images_chk.toggled.connect(self._toggle_front_folder)

        input_row = QHBoxLayout()
        self.input_label = QLabel("No input folder selected")
        self.input_label.setStyleSheet("color: red;")
        input_row.addWidget(self.input_label, stretch=1)
        pick_input = QPushButton("Select Input Folder")
        pick_input.clicked.connect(self._pick_input_folder)
        input_row.addWidget(pick_input)
        layout.addLayout(input_row)

        actions_row = QHBoxLayout()
        self.fetch_btn = QPushButton("Fetch sku2asin")
        self.fetch_btn.clicked.connect(self._fetch_sku2asin)
        actions_row.addWidget(self.fetch_btn)

        actions_row.addStretch(1)

        self.start_btn = QPushButton("Start")
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_workflow)
        actions_row.addWidget(self.start_btn)

        layout.addLayout(actions_row)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(spacer)

        self._set_central(menu)

    # ------------------------------------------------------------------
    def _toggle_front_folder(self, checked: bool) -> None:
        self.btn_front_folder.setEnabled(checked)
        if not checked:
            self.front_image_folder = None
            self.front_image_label.setText("No front image folder selected")
            self.front_image_label.setStyleSheet("color: red;")

    def _pick_input_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose TOP-LEVEL input folder")
        if folder:
            self.input_folder = folder
            self.input_label.setText(f"Input: {os.path.basename(folder)}")
            self.input_label.setStyleSheet("color: green;")
            self._update_start_enabled()
        else:
            self.input_folder = None
            self.input_label.setText("No input folder selected")
            self.input_label.setStyleSheet("color: red;")
            self._update_start_enabled()

    def _pick_front_image_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose FRONT IMAGES folder")
        if folder:
            self.front_image_folder = folder
            self.front_image_label.setText(f"Front Images: {os.path.basename(folder)}")
            self.front_image_label.setStyleSheet("color: green;")
        else:
            self.front_image_folder = None
            self.front_image_label.setText("No front image folder selected")
            self.front_image_label.setStyleSheet("color: red;")

    def _fetch_sku2asin(self) -> None:
        try:
            # Import and call the function directly instead of subprocess
            from fetch_sku2asin import fetch_sku2asin
            message = fetch_sku2asin()
            self.fetch_completed = True
            QMessageBox.information(self, "sku2asin fetch", message)
        except Exception as e:
            self.fetch_completed = False
            QMessageBox.critical(self, "sku2asin fetch", f"Failed to fetch sku2asin:\n{str(e)}")
        self._update_start_enabled()

    def _update_start_enabled(self) -> None:
        self.start_btn.setEnabled(bool(self.input_folder) and self.fetch_completed)

    def _start_workflow(self) -> None:
        if not self.input_folder:
            QMessageBox.warning(self, "Input required", "Please choose an input folder before starting.")
            return
        self._copy_front_images = self.front_images_chk.isChecked()
        self.resize(960, 800)
        if self.colours_sorted_chk.isChecked():
            self._show_phase(OrderPhase, self._on_order_done)
        else:
            self._show_phase(ColorPhase, self._on_colour_done)

    def _show_phase(self, phase_class, callback) -> None:
        if self.phase_widget:
            self.phase_widget.deleteLater()
            self.phase_widget = None
        self.phase_widget = phase_class(root_dir=self.input_folder, on_complete=callback)
        self._set_central(self.phase_widget)

    def _on_colour_done(self, colour_output: str) -> None:
        self.input_folder = colour_output
        self._show_phase(OrderPhase, self._on_order_done)

    def _on_order_done(self, pt_output: str | None = None) -> None:
        self._pending_pt_output = pt_output
        self._show_processing_screen()
        QTimer.singleShot(0, self._finish_processing)

    def _show_processing_screen(self) -> None:
        processing = QWidget()
        layout = QVBoxLayout(processing)
        layout.setAlignment(Qt.AlignCenter)  # type: ignore
        label = QLabel("Sorting complete, processing")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        self._set_central(processing)

    def _finish_processing(self) -> None:
        pt_output = self._pending_pt_output
        if pt_output:
            if self._copy_front_images and self.front_image_folder:
                run_front_images(pt_output, self.front_image_folder, self)
            try:
                import amz_rename

                amz_rename.run(pt_output)
            except Exception as exc:  # pragma: no cover - defensive
                QMessageBox.critical(self, "amz_rename error", str(exc))
        self.close()


def main() -> int:
    app = QApplication(sys.argv)
    window = CombinedApp()
    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
