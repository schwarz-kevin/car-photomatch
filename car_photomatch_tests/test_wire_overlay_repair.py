"""Tests that forced object-level wireframe is disabled without touching models."""
import ast
from pathlib import Path
from types import SimpleNamespace

src = Path(__file__).parent.parent / 'car_photomatch' / 'rim_mode.py'
tree = ast.parse(src.read_text())


def extract(name, namespace):
    node = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(src), 'exec'), namespace)
    return namespace[name]


def mesh(name, parent):
    return SimpleNamespace(name=name, parent=parent, type='MESH',
                           show_wire=True, show_all_edges=True, display_type='WIRE')


def test_repairs_existing_guides_only():
    ns = {'_RIM_GUIDE_PREFIXES': (
        'Photo Edge - measured circle', 'Bead Seat - nominal diameter',
        'Rear Width Reference - approximate', 'Wheel Axis', 'Face X Axis',
        'Face Y Axis', 'Lug Guide ', 'Lug Guides (', 'Hub Mount Plane - Center Bore',
    )}
    extract('_is_rim_guide_mesh', ns)
    repair = extract('_repair_rim_guide_wire', ns)
    root = SimpleNamespace(name='RIM PM - Rig Root (XY face)')
    other_parent = SimpleNamespace(name='MyModel')
    guide = mesh('Photo Edge - measured circle', root)
    old_lug = mesh('Lug Guide 03', root)
    old_hub = mesh('Hub Mount Plane - Center Bore (ET +35)', root)
    user_model = mesh('Spokes', root)
    not_a_rig = mesh('Photo Edge - measured circle', other_parent)
    scene = SimpleNamespace(objects=[guide,old_lug,old_hub,user_model,not_a_rig])
    assert repair(scene) == 3
    for o in (guide,old_lug,old_hub):
        assert o.display_type == 'SOLID'
        assert not o.show_wire and not o.show_all_edges
    for o in (user_model,not_a_rig):
        assert o.display_type == 'WIRE'
        assert o.show_wire and o.show_all_edges


def test_wire_cleanup_operator_and_ui_present():
    code = src.read_text()
    assert "rim_pm.repair_guide_wire" in code
    assert "Fix Old Rig Wire Overlays" in code
    assert "obj.show_wire = True" not in code
    assert "obj.show_all_edges = True" not in code
    assert ".shading.type =" not in code
