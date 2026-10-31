"""v0.4.7 photographed-ring classification and unchanged solver/shading checks."""
import ast
import hashlib
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

EXT = Path(__file__).resolve().parents[1] / 'car_photomatch'
spec = importlib.util.spec_from_file_location('rim_guides_047', EXT/'rim_guides.py')
rg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rg)


@pytest.mark.parametrize('ring,overhang,et,expected', [
    ('MANUAL', 12, 35, -20),
    ('FRONT_BEAD', 12, 35, 0),
    ('REAR_BEAD', 12, 35, 241.3),
    ('FRONT_LIP', 12, 35, -12),
    ('REAR_LIP', 12, 35, 253.3),
    ('HUB_FACE', 12, 35, 85.65),
    ('HUB_FACE', 12, -35, 155.65),
    ('FRONT_LIP', 18, 35, -18),
    ('REAR_LIP', 18, 35, 259.3),
])
def test_photo_ring_identity_to_front_bead_z(ring, overhang, et, expected):
    assert rg.photo_ring_front_bead_z_mm(9.5, et, ring, overhang, -20) == pytest.approx(expected)


@pytest.mark.parametrize('ring,expected', [
    ('FRONT_BEAD', -85.65),
    ('REAR_BEAD', 155.65),
    ('FRONT_LIP', -97.65),
    ('REAR_LIP', 167.65),
    ('HUB_FACE', 0),
    ('MANUAL', -105.65),
])
def test_mounting_plane_matches_photo_reference(ring, expected):
    front = rg.photo_ring_front_bead_z_mm(9.5, 35, ring, 12, -20)
    result = rg.mounting_face_z_m(9.5, 35, front) * 1000
    assert result == pytest.approx(expected)


@pytest.mark.parametrize('args', [
    (0, 35, 'FRONT_BEAD', 12, 0),
    (9.5, 35, 'FRONT_LIP', -2, 0),
    (9.5, 35, 'UNKNOWN', 12, 0),
    (9.5, math.nan, 'FRONT_BEAD', 12, 0),
    (9.5, 35, 'FRONT_BEAD', math.inf, 0),
])
def test_bad_input(args):
    with pytest.raises(ValueError):
        rg.photo_ring_front_bead_z_mm(*args)


def test_existing_manual_setting_unchanged_by_v047_default():
    source = (EXT/'rim_mode.py').read_text()
    assert "photo_ring_type: EnumProperty(name='Detected Ring Type', default='MANUAL'" in source
    assert 'default=-12.' in source
    manual = rg.photo_ring_front_bead_z_mm(9.5, 35, 'MANUAL', 12, -18.5)
    assert manual == -18.5


def test_only_generated_rig_reference_z_is_updated():
    src = EXT/'rim_mode.py'
    tree = ast.parse(src.read_text())
    names = {'_front_bead_z_mm','_sync_rig_reference_depths'}
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    ns = {'rim_guides':rg}
    exec(compile(ast.Module(body=fns,type_ignores=[]),str(src),'exec'),ns)

    class Vertex:
        def __init__(self, xyz): self.co = SimpleNamespace(x=xyz[0], y=xyz[1], z=xyz[2])
    class Mesh:
        def __init__(self, xyz):
            self.vertices = [Vertex(v) for v in xyz]
            self.updates = 0
        def update(self): self.updates += 1
    def obj(name, coords, obj_type='MESH'):
        return SimpleNamespace(name=name, type=obj_type, data=Mesh(coords))
    front = obj('Bead Seat - nominal diameter', [(0.2, 0, -0.012),(0,0.2,-0.012)])
    back = obj('Rear Width Reference - approximate', [(0.2, 0, -0.2533)])
    axis = obj('Wheel Axis', [(0,0,-0.35),(0,0,0.1)])
    other = obj('Important Custom Model', [(1,2,3)])
    root = SimpleNamespace(children=[front,back,axis,other])
    settings=SimpleNamespace(width_in=9.5, offset_et_mm=35., photo_ring_type='REAR_BEAD',
                             lip_overhang_mm=12., front_bead_seat_z_mm=-12.)
    ns['_sync_rig_reference_depths'](root, settings)
    assert all(v.co.z == pytest.approx(.2413) for v in front.data.vertices)
    assert back.data.vertices[0].co.z == pytest.approx(0)
    assert axis.data.vertices[0].co.z == pytest.approx(-.1)
    assert axis.data.vertices[1].co.z == pytest.approx(.1)
    assert other.data.vertices[0].co.z == 3
    assert other.data.updates == 0
    assert front.data.vertices[0].co.x == .2


def test_original_solver_and_display_are_unchanged():
    # Fixed known-good hashes from v0.4.6; these do not require an external copy.
    hashes = {
        'solver.py': 'e2cb69407b3ca53d63741449528b1ae7c2d49dd29a61eb6abf67bae9db81f974',
        'rim_core.py': '7a5a451072c533c311aa42e3ff372da21e61ca6aa20e2d7f98872229dd017caf',
    }
    for name, expected in hashes.items():
        assert hashlib.sha256((EXT/name).read_bytes()).hexdigest() == expected
    code = (EXT/'__init__.py').read_text()
    assert "'version': (0, 4, 12)" in code
    assert 'def _apply_view_display(' not in code
    assert '_apply_photo_display' in code


def test_ui_presents_each_ring_type():
    src=(EXT/'rim_mode.py').read_text()
    for marker in ("'FRONT_BEAD'", "'REAR_BEAD'", "'FRONT_LIP'", "'REAR_LIP'", "'HUB_FACE'", "'MANUAL'"):
        assert marker in src
    assert "ring_box.prop(s, 'photo_ring_type'" in src
    assert 'Update Ring & ET Guides' in src
