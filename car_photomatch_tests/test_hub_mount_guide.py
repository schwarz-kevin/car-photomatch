"""v0.4.6: physically defined mounting-face guide for wheel offset ET."""
import ast
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import math
import pytest

EXT = Path(__file__).resolve().parents[1] / 'car_photomatch'
spec = importlib.util.spec_from_file_location('rim_guides_046', EXT/'rim_guides.py')
rg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rg)


def test_et_geometry_signs_and_units():
    # Selected photo edge at z=0; first bead seat located 12mm behind it.
    front = -12
    half_width = 9.5 * 25.4 / 2
    assert rg.mounting_face_z_m(9.5, 0, front) * 1000 == pytest.approx(front - half_width)
    assert rg.mounting_face_z_m(9.5, 35, front) * 1000 == pytest.approx(-97.65)
    assert rg.mounting_face_z_m(9.5, -35, front) * 1000 == pytest.approx(-167.65)
    assert rg.mounting_face_z_m(9.5, 35, front) - rg.mounting_face_z_m(9.5, -35, front) == pytest.approx(.070)
    assert rg.mounting_face_z_m(9.5, 0, front) == pytest.approx(-.13265)


def test_reference_position_is_relative_to_selected_edge():
    # Marked ring could also be a center cap or a ring in the barrel.
    a = rg.mounting_face_z_m(8.5, 40, -12)
    b = rg.mounting_face_z_m(8.5, 40, -27)
    assert (a-b)*1000 == pytest.approx(15.)


@pytest.mark.parametrize('input_', [(-1, 35, -12), (0, 35, -12),
                                    (9.5, math.inf, -12),
                                    (9.5, 35, math.nan)])
def test_invalid_geometry(input_):
    with pytest.raises(ValueError):
        rg.mounting_face_z_m(*input_)


def test_closed_center_bore_guide_circle():
    v,e = rg.circle_edge_loop(0.0666/2, 64, z=-.09765)
    assert len(v) == len(e) == 64
    assert e[-1] == (63,0)
    assert all(pt[2] == -.09765 for pt in v)
    assert math.dist(v[0], (0.0333,0.,-.09765)) < 1e-12
    assert all(abs(math.hypot(x,y)-.0333) < 1e-12 for x,y,z in v)


class FakeMesh:
    def __init__(self):
        self.verts = self.edges = self.faces = None
        self.updated = False
        self.clear_count = 0
    def from_pydata(self, vs, es, fs):
        self.verts,self.edges,self.faces = vs,es,fs
    def update(self): self.updated = True
    def clear_geometry(self):
        self.clear_count += 1
        self.verts = self.edges = self.faces = None


class FakeObj:
    def __init__(self, name, mesh):
        self.name = name
        self.data = mesh
        self.type = 'MESH'
        self._tags = {}
        self.location = (0.,0.,0.)
    def get(self, key): return self._tags.get(key)
    def __setitem__(self, key, value): self._tags[key] = value
    def __getitem__(self, key): return self._tags[key]


class FakeGroup:
    def __init__(self):
        self.root = SimpleNamespace(children=[])
        def add(x): self.root.children.append(x)
        self.objects = SimpleNamespace(link=add)


def test_create_then_update_is_one_object_and_mesh():
    src = EXT/'rim_mode.py'
    tree = ast.parse(src.read_text())
    fmts = ('_finalize_rig_mesh','_new_rig_circle_mesh','_front_bead_z_mm','_hub_guide_z','_sync_rig_reference_depths','_sync_rig_bead_circle_diameters','_sync_rig_photo_diameter','_effective_edge_diameter','_update_hub_guide')
    func_ast = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in fmts]
    const_ast = [n for n in tree.body if isinstance(n,ast.Assign) and
                 any(isinstance(t,ast.Name) and t.id == '_HUB_GUIDE_ROLE' for t in n.targets)]
    fake_meshes = []
    fake_objects = []
    def meshnew(name):
        x = FakeMesh(); fake_meshes.append(x); return x
    def objnew(name, mesh):
        x = FakeObj(name, mesh); fake_objects.append(x); return x
    ns = {'bpy': SimpleNamespace(data=SimpleNamespace(meshes=SimpleNamespace(new=meshnew),
                                                     objects=SimpleNamespace(new=objnew))),
          'rim_guides':rg, 'math':math}
    exec(compile(ast.Module(body=const_ast+func_ast,type_ignores=[]),str(src),'exec'),ns)
    group = FakeGroup()
    settings = SimpleNamespace(width_in=9.5, offset_et_mm=35., photo_ring_type='MANUAL', lip_overhang_mm=12., front_bead_seat_z_mm=-12.,
                               center_bore_mm=66.6, circle_vertices=32, nominal_diameter_in=19.,
                                   edge_diameter_mm=500., override_edge_diameter=False)
    guide = ns['_update_hub_guide'](group.root, group, settings)
    assert len(group.root.children)==len(fake_objects)==len(fake_meshes)==1
    assert len(guide.data.verts)==32
    assert guide.data.verts[0][2] == pytest.approx(-.09765)
    assert guide.display_type == 'SOLID'
    assert guide.data.faces == []
    settings.offset_et_mm = -20
    settings.center_bore_mm = 72.6
    settings.circle_vertices = 48
    guide2 = ns['_update_hub_guide'](group.root, group, settings)
    assert guide2 is guide
    assert len(group.root.children)==len(fake_objects)==len(fake_meshes)==1
    assert guide2.data.clear_count==1
    assert len(guide2.data.verts)==48
    assert guide2.data.verts[0][2] == pytest.approx(rg.mounting_face_z_m(9.5,-20.,-12.))
    assert guide2['rim_pm_et_mm'] == -20
    assert guide2['rim_pm_center_bore_mm'] == 72.6


def test_ui_and_registration_has_et_guide_and_no_solver_or_shading_changes():
    source = (EXT/'rim_mode.py').read_text()
    assert 'class RIMPM_OT_UpdateHubGuide' in source
    assert 'box.prop(s, \'offset_et_mm\')' in source
    assert 'box.prop(s, \'center_bore_mm\')' in source
    assert "body.prop(s, 'front_bead_seat_z_mm')" in source
    assert "body.operator('rim_pm.update_hub_guide'" in source
    assert 'RIMPM_OT_UpdateHubGuide' in source.split('CLASSES = (',1)[1]
    import hashlib
    for f, expected in [('rim_core.py','7a5a451072c533c311aa42e3ff372da21e61ca6aa20e2d7f98872229dd017caf'), ('solver.py','e2cb69407b3ca53d63741449528b1ae7c2d49dd29a61eb6abf67bae9db81f974')]:
        assert hashlib.sha256((EXT/f).read_bytes()).hexdigest() == expected
    assert "'version': (0, 4, 12)" in (EXT/'__init__.py').read_text()
