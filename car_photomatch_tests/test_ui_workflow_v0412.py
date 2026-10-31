"""UI-layout regression checks: no Blender runtime required."""
import ast
from pathlib import Path
from types import SimpleNamespace

SRC = Path(__file__).parent.parent / 'car_photomatch' / 'rim_mode.py'
TREE = ast.parse(SRC.read_text())


def ui_function():
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == '_panel_ui')
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC), 'exec'), namespace)
    return namespace['_panel_ui']


class RecordedLayout:
    def __init__(self, events, kind='root'):
        self.events = events
        self.kind = kind
        self.enabled = True

    def label(self, *, text, icon=None):
        self.events.append(('label', text))

    def prop(self, _settings, propname, *, text=None):
        self.events.append(('prop', propname, text))

    def panel(self, panel_id, *, default_closed):
        self.events.append(('panel', panel_id, default_closed))
        return self, None  # All sections start collapsed; no content drawn.

    def row(self, *, align=False):
        self.events.append(('row', self.kind))
        return RecordedLayout(self.events, 'action')

    def operator(self, op_id, *, text, icon):
        self.events.append(('operator', op_id, text, self.enabled))


def recorded(image_editor, rig_exists=False):
    events = []
    root = RecordedLayout(events)
    s = SimpleNamespace(image=None, rig_root=object() if rig_exists else None)
    ctx = SimpleNamespace(scene=SimpleNamespace(rim_pm=s))
    ui_function()(root, ctx, image_editor=image_editor)
    return events


def test_all_sections_start_collapsed_in_image_editor_and_3d_viewport():
    for image_editor in (False, True):
        events = recorded(image_editor)
        panels = [e for e in events if e[0] == 'panel']
        assert [p[1] for p in panels] == [
            'rimpm_v0412_photo_and_edge', 'rimpm_v0412_rim_geometry',
            'rimpm_v0412_lug_guides', 'rimpm_v0412_hub_et',
            'rimpm_v0412_camera', 'rimpm_v0412_advanced',
        ]
        assert all(p[2] is True for p in panels)


def test_create_rig_is_always_visible_after_et_before_camera():
    for image_editor in (False, True):
        e = recorded(image_editor)
        i_hub = next(i for i, x in enumerate(e) if x[:2] == ('panel', 'rimpm_v0412_hub_et'))
        i_create = next(i for i, x in enumerate(e) if x[:2] == ('operator', 'rim_pm.create_rig'))
        i_cam = next(i for i, x in enumerate(e) if x[:2] == ('panel', 'rimpm_v0412_camera'))
        assert i_hub < i_create < i_cam
        assert e[i_create] == ('operator', 'rim_pm.create_rig', 'Create Modeling Rig', True)
        assert sum(x[:2] == ('operator','rim_pm.create_rig') for x in e) == 1


def test_create_button_disabled_if_existing_rig_but_section_order_still_correct():
    e = recorded(False, rig_exists=True)
    assert ('operator', 'rim_pm.create_rig', 'Create Modeling Rig', False) in e
    assert sum(x[0] == 'panel' for x in e) == 6


def test_previous_controls_remain_reachable_when_sections_expand():
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == '_panel_ui')
    source = ast.get_source_segment(SRC.read_text(), node)
    for op in ('rim_pm.load_photo', 'rim_pm.pick_area', 'rim_pm.detect',
               'rim_pm.manual_points', 'rim_pm.switch_candidate',
               'rim_pm.update_ring_guides', 'rim_pm.update_hub_guide',
               'rim_pm.create_rig', 'rim_pm.solve', 'rim_pm.switch_solution',
               'rim_pm.view_camera', 'rim_pm.repair_guide_wire'):
        assert op in source
    assert source.count("operator('rim_pm.create_rig'") == 1
