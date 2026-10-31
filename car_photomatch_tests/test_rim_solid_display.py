"""Focused geometry + viewport regression tests for experimental v0.4.3."""
import ast
import math
from pathlib import Path
from types import SimpleNamespace

SRC = Path(__file__).parent.parent / 'car_photomatch' / 'rim_mode.py'
TREE = ast.parse(SRC.read_text())


def extract(name, namespace):
    node = next(item for item in TREE.body if isinstance(item, ast.FunctionDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SRC), 'exec'), namespace)
    return namespace[name]


class FakeMesh:
    def __init__(self):
        self.verts = None
        self.edges = None
        self.faces = None

    def from_pydata(self, verts, edges, faces):
        self.verts, self.edges, self.faces = verts, edges, faces

    def update(self):
        pass


class FakeMeshes:
    def new(self, name):
        return FakeMesh()


class FakeObjects:
    def new(self, name, mesh):
        return SimpleNamespace(name=name, data=mesh, type='MESH')


class FakeCollection:
    class Linker:
        def link(self, obj):
            pass
    objects = Linker()


def test_mesh_circle_unfilled_has_editable_edge_loop_and_solid_object_display():
    ns = {'bpy': SimpleNamespace(data=SimpleNamespace(meshes=FakeMeshes(), objects=FakeObjects())), 'math': math}
    extract('_finalize_rig_mesh', ns)
    func = extract('_new_rig_circle_mesh', ns)
    root = object()
    o = func(root, FakeCollection(), 'Guide', 0.25, 0.0, segments=32)
    assert len(o.data.verts) == 32
    assert len(o.data.edges) == 32
    assert len(o.data.faces) == 0
    assert o.display_type == 'SOLID'
    assert not o.show_wire and not o.show_all_edges
    assert o.parent is root


def test_fill_option_generates_shadeable_ngon():
    ns = {'bpy': SimpleNamespace(data=SimpleNamespace(meshes=FakeMeshes(), objects=FakeObjects())), 'math': math}
    extract('_finalize_rig_mesh', ns)
    func = extract('_new_rig_circle_mesh', ns)
    obj = func(object(), FakeCollection(), 'Filled', 0.25, 0.0, segments=48, filled=True)
    assert len(obj.data.verts) == 48
    assert len(obj.data.faces) == 1
    assert len(obj.data.faces[0]) == 48


def test_no_shading_reset_operator_in_rim_mode():
    src = SRC.read_text()
    assert 'rim_pm.restore_solid' not in src
    assert 'RIMPM_OT_RestoreSolid' not in src
    assert '.shading.type =' not in src
    assert "obj.display_type = 'WIRE'" not in src
    assert "obj.display_type = 'SOLID'" in src
