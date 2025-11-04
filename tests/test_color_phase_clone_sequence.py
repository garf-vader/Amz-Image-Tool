import os

import pytest
from PIL import Image

pytest.importorskip("PyQt5.QtWidgets")
from PyQt5.QtWidgets import QApplication

import color_phase


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        # Use the offscreen platform to avoid GUI requirements in tests
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication([])
    return app


def _create_image(path):
    img = Image.new("RGB", (32, 32), color=(255, 0, 0))
    img.save(path)


def test_clone_removed_from_colour_sequence(monkeypatch, tmp_path):
    _ensure_app()

    root = tmp_path / "root"
    leaf = root / "leaf"
    leaf.mkdir(parents=True)

    for idx in range(6):
        _create_image(leaf / f"img_{idx}.png")

    output_root = tmp_path / "outputs"
    monkeypatch.setattr(color_phase, "get_output_root", lambda _base: str(output_root))

    phase = color_phase.ColorPhase(str(root), lambda _path: None)

    for entry, colour in zip(phase.color_entries, ["Blue", "Black", "Green"]):
        entry.setText(colour)

    phase.apply_colors()
    initial = [item.assigned_color for item in phase.items[:6]]
    assert initial == ["Blue", "Black", "Green", "Blue", "Black", "Green"]

    phase._set_clone_item(phase.items[2])
    updated = [item.assigned_color for item in phase.items[:6]]
    assert updated == ["Blue", "Black", "Clone", "Green", "Blue", "Black"]

    # Unset clone to confirm sequence returns to normal cycling
    phase._set_clone_item(None)
    reverted = [item.assigned_color for item in phase.items[:6]]
    assert reverted == ["Blue", "Black", "Green", "Blue", "Black", "Green"]
