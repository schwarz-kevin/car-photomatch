"""Regression tests for automatic photo-ring scale (v0.4.8)."""
import ast
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

EXT = Path(__file__).resolve().parents[1] / 'car_photomatch'
spec = importlib.util.spec_from_file_location('rim_guides_048', EXT / 'rim_guides.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

@pytest.mark.parametrize('ring,center,expected,status', [
    ('FRONT_BEAD',66.6,482.6,'EXACT_BEAD'),
    ('REAR_BEAD',66.6,482.6,'EXACT_BEAD'),
    ('CENTER_BORE',72.6,72.6,'CENTER_BORE'),
    ('HUB_FACE',72.6,72.6,'ASSUMED_CENTER_BORE'),
    ('FRONT_LIP',66.6,482.6,'APPROX_BEAD'),
    ('REAR_LIP',66.6,482.6,'APPROX_BEAD'),
    ('MANUAL',66.6,482.6,'APPROX_BEAD'),
])
def test_auto_diameter_for_ring_types(ring,center,expected,status):
    d, flag = g.effective_photo_ring_diameter_mm(19,ring,center)
    assert d == pytest.approx(expected)
    assert flag == status

def test_manual_measurement_only_if_explicit_override():
    assert g.effective_photo_ring_diameter_mm(19,'FRONT_BEAD',66.6,500,False)[0] == pytest.approx(482.6)
    assert g.effective_photo_ring_diameter_mm(19,'FRONT_BEAD',66.6,500,True) == (500,'OVERRIDE')

@pytest.mark.parametrize('params',[(0,'FRONT_BEAD'), (19,'UNKNOWN'), (math.inf,'FRONT_BEAD')])
def test_auto_diameter_validation(params):
    with pytest.raises(ValueError):
        g.effective_photo_ring_diameter_mm(*params)

def test_center_bore_uses_mounting_plane():
    front = g.photo_ring_front_bead_z_mm(9.5, 35, 'CENTER_BORE')
    assert g.mounting_face_z_m(9.5,35,front) == pytest.approx(0)

def test_effective_diameter_used_in_solver_and_rig_and_display():
    source=(EXT/'rim_mode.py').read_text()
    assert 'edge_radius = _effective_edge_diameter(s)[0] / 2000.' in source
    assert 'ellipse, _effective_edge_diameter(s)[0], fx, fy, cx, cy' in source
    assert 'if s.override_edge_diameter:' in source
    assert "body.prop(s, 'edge_diameter_mm')" in source
    assert "col.prop(s, 'edge_diameter_mm')" not in source
    assert 'RIMPM_OT_UpdateRingGuides' in source

def test_update_changes_only_generated_photo_guides():
    src=EXT/'rim_mode.py'
    tree=ast.parse(src.read_text())
    names={'_sync_rig_photo_diameter','_effective_edge_diameter'}
    funs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    scope={'rim_guides':g, 'math':math}
    exec(compile(ast.Module(body=funs,type_ignores=[]),str(src),'exec'),scope)
    class Mesh:
        def __init__(self, vertices):
            self.vertices=[SimpleNamespace(co=SimpleNamespace(x=x,y=y,z=z)) for x,y,z in vertices]
            self.updates=0
        def update(self):self.updates+=1
    def obj(n,v):return SimpleNamespace(type='MESH',name=n,data=Mesh(v))
    measured=obj('Photo Edge - measured circle',[(.25,0,0),(0,.25,0),(-.25,0,0),(0,-.25,0)])
    xax=obj('Face X Axis',[(-.25,0,0),(.25,0,0)])
    yax=obj('Face Y Axis',[(0,-.25,0),(0,.25,0)])
    custom=obj('My Important Rim Geometry',[(1,2,3)])
    root=SimpleNamespace(children=[measured,xax,yax,custom])
    settings=SimpleNamespace(nominal_diameter_in=19.,photo_ring_type='FRONT_BEAD',
                            center_bore_mm=66.6,edge_diameter_mm=500.,override_edge_diameter=False)
    scope['_sync_rig_photo_diameter'](root,settings)
    radius=482.6/2000
    assert measured.data.vertices[0].co.x == pytest.approx(radius)
    assert measured.data.vertices[1].co.y == pytest.approx(radius)
    assert xax.data.vertices[0].co.x == pytest.approx(-radius)
    assert yax.data.vertices[1].co.y == pytest.approx(radius)
    assert custom.data.vertices[0].co.z == 3
    assert custom.data.updates == 0
