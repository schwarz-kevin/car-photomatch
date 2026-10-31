"""Regression guard for Image Editor panel hidden by removed Blender UI icon."""
from pathlib import Path


def test_rim_area_operator_visible_without_removed_icon():
    src = (Path(__file__).parent.parent / 'car_photomatch' / 'rim_mode.py').read_text()
    assert "col.operator('rim_pm.pick_area', text='1. Draw Rim Area')" in src
    assert "icon='BORDER_RECT'" not in src
    assert "bl_idname = 'rim_pm.pick_area'" in src
    assert 'image_editor=True' in src
