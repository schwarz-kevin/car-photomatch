"""v0.4.5: lug-hole guides are a single mesh of disconnected edge loops."""
import ast
import importlib.util
import math
from pathlib import Path
from types import SimpleNamespace

import pytest

EXT = Path(__file__).resolve().parents[1] / 'car_photomatch'
spec = importlib.util.spec_from_file_location('rim_guides', EXT / 'rim_guides.py')
rim_guides = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rim_guides)


def test_lug_count_and_vertex_count_and_closed_edge_loops():
    n, segs = 5, 28
    vertices, edges = rim_guides.lug_guide_mesh(n, 0.1143 / 2, .014 / 2, segs)
    assert len(vertices) == n * segs
    assert len(edges) == n * segs
    for i in range(n):
        start = i * segs
        ring_edges = edges[start:start + segs]
        assert ring_edges[-1] == (start + segs - 1, start)
        assert {v for edge in ring_edges for v in edge} == set(range(start, start + segs))
        xs = [x for x, y, z in vertices[start:start + segs]]
        ys = [y for x, y, z in vertices[start:start + segs]]
        center_x = sum(xs) / segs
        center_y = sum(ys) / segs
        a = math.tau * i / n
        assert center_x == pytest.approx(.1143 / 2 * math.cos(a), abs=1e-10)
        assert center_y == pytest.approx(.1143 / 2 * math.sin(a), abs=1e-10)
        assert all(z == 0.0 for x, y, z in vertices[start:start + segs])


@pytest.mark.parametrize('count,segs', [(3, 6), (4, 16), (5, 48), (6, 64), (8, 128), (12, 256)])
def test_pattern_counts(count, segs):
    vertices, edges = rim_guides.lug_guide_mesh(count, .05, .008, segs, z=.003)
    assert len(vertices) == count * segs
    assert len(edges) == count * segs
    assert all(z == .003 for x, y, z in vertices)


@pytest.mark.parametrize('values', [(2, .05, .007, 12), (13, .05, .007, 12),
                                    (5, .05, .007, 5), (5, .05, .007, 257),
                                    (5, 0, .007, 16), (5, .05, 0, 16)])
def test_invalid_dimensions_rejected(values):
    with pytest.raises(ValueError):
        rim_guides.lug_guide_mesh(*values)


class FakeMesh:
    def from_pydata(self, verts, edges, faces):
        self.verts = verts
        self.edges = edges
        self.faces = faces

    def update(self):
        self.updated = True


class FakeMeshes:
    def __init__(self):
        self.created = []

    def new(self, name):
        mesh = FakeMesh()
        self.created.append((name, mesh))
        return mesh


class FakeObjects:
    def __init__(self):
        self.created = []

    def new(self, name, mesh):
        obj = SimpleNamespace(name=name, type='MESH', data=mesh)
        self.created.append(obj)
        return obj


class FakeCollection:
    def __init__(self):
        self.items = []
        self.objects = SimpleNamespace(link=self.items.append)


def test_blender_adapter_creates_exactly_one_mesh_object():
    src = EXT / 'rim_mode.py'
    tree = ast.parse(src.read_text())
    ns = {
        'rim_guides': rim_guides,
        'bpy': SimpleNamespace(data=SimpleNamespace(meshes=FakeMeshes(), objects=FakeObjects()))
    }
    for name in ('_finalize_rig_mesh', '_create_lug_guides'):
        func = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(src), 'exec'), ns)
    root = object()
    coll = FakeCollection()
    obj = ns['_create_lug_guides'](root, coll, 5, .1143/2, .014/2, 0., segments=32)
    assert len(ns['bpy'].data.meshes.created) == 1
    assert len(ns['bpy'].data.objects.created) == 1
    assert len(coll.items) == 1
    assert obj is coll.items[0]
    assert obj.parent is root
    assert obj.display_type == 'SOLID'
    assert len(obj.data.verts) == len(obj.data.edges) == 160
    assert obj.data.faces == []
    assert '5x114.3' in obj.name


def test_ui_has_independent_lug_slider_and_original_rim_controls():
    source = (EXT / 'rim_mode.py').read_text()
    assert "lug_circle_vertices: IntProperty" in source
    assert "body.prop(s, 'lug_circle_vertices', text='Lug Vertices', slider=True)" in source
    assert "body.prop(s, 'circle_vertices', text='Rim Circle Vertices')" in source
    assert "segments=s.lug_circle_vertices" in source
    assert "body.prop(s, 'lug_count', text='Lug Count')" in source
    assert "body.prop(s, 'pcd_mm', text='PCD (mm)')" in source
    assert "body.prop(s, 'lug_diameter_mm', text='Hole Diameter (mm)')" in source


def test_no_solver_regression():
    import hashlib
    assert hashlib.sha256((EXT / 'rim_core.py').read_bytes()).hexdigest() == '7a5a451072c533c311aa42e3ff372da21e61ca6aa20e2d7f98872229dd017caf'
    assert hashlib.sha256((EXT / 'solver.py').read_bytes()).hexdigest() == 'e2cb69407b3ca53d63741449528b1ae7c2d49dd29a61eb6abf67bae9db81f974'
    assert "'version': (0, 4, 12)" in (EXT / '__init__.py').read_text()
