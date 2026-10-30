"""Blender-free tests of actual v0.3 global display helpers via AST extraction."""
import ast
import pathlib
import types
import unittest

ADDON = pathlib.Path(__file__).resolve().parents[1] / 'car_photomatch' / '__init__.py'
tree = ast.parse(ADDON.read_text(encoding='utf8'))
helper_names = {'_apply_photo_display', '_iter_scene_viewports', '_apply_view_display',
                '_camera_reference', '_apply_model_in_front'}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
         and node.name in helper_names]
ns = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ADDON), 'exec'), ns)


class FakeCameraData:
    def __init__(self, images=(), lens=55.):
        self.background_images = [types.SimpleNamespace(image=i, alpha=.9,
                                                        display_depth='BACK') for i in images]
        self.show_background_images = True
        self.lens = lens
        self._identity = id(self)

    def as_pointer(self):
        return self._identity


class FakeCamera:
    type = 'CAMERA'

    def __init__(self, name, data):
        self.name, self.data = name, data
        self.matrix_world = ('pose', name)


class FakeArea:
    type = 'VIEW_3D'

    def __init__(self):
        self.spaces = types.SimpleNamespace(active=types.SimpleNamespace(
            shading=types.SimpleNamespace(type='WIREFRAME', show_xray=False,
                                          xray_alpha=0.8)))
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


class GlobalDisplayTests(unittest.TestCase):
    def setUp(self):
        self.old_photo = types.SimpleNamespace(name='old.png')
        self.new_photo = types.SimpleNamespace(name='new.png')
        self.old = FakeCamera('old, renamed v0.2 camera', FakeCameraData([self.old_photo]))
        self.new = FakeCamera('new v0.3 camera', FakeCameraData([self.new_photo]))
        self.non_camera = types.SimpleNamespace(type='MESH', name='CAR')
        self.scene = types.SimpleNamespace(objects=[self.old, self.new, self.non_camera])
        self.s = types.SimpleNamespace(opacity=.37, photo_depth='FRONT',
                                       show_camera_photo=True,
                                       view_shading='SOLID', use_xray=True,
                                       model_opacity=.27)

    def test_all_cameras_including_legacy_are_changed(self):
        ns['_apply_photo_display'](self.scene, self.s)
        for cam in [self.old, self.new]:
            self.assertEqual(cam.data.background_images[0].alpha, .37)
            self.assertEqual(cam.data.background_images[0].display_depth, 'FRONT')
            self.assertTrue(cam.data.show_background_images)
            self.assertEqual(cam.matrix_world, ('pose', cam.name))
            self.assertEqual(cam.data.lens, 55.)

    def test_background_visibility_global(self):
        self.s.show_camera_photo = False
        ns['_apply_photo_display'](self.scene, self.s)
        self.assertFalse(self.old.data.show_background_images)
        self.assertFalse(self.new.data.show_background_images)
        self.assertEqual(ns['_camera_reference'](self.old), self.old_photo)

    def test_cameras_without_photo_are_not_changed(self):
        blank = FakeCamera('blank', FakeCameraData([]))
        self.scene.objects.append(blank)
        ns['_apply_photo_display'](self.scene, self.s)
        self.assertTrue(blank.data.show_background_images)

    def test_view_controls_update_all_scene_windows_only(self):
        first, second, other_scene = FakeArea(), FakeArea(), FakeArea()
        other_scene_ptr = object()
        wm = types.SimpleNamespace(windows=[
            types.SimpleNamespace(scene=self.scene, screen=types.SimpleNamespace(areas=[first, second])),
            types.SimpleNamespace(scene=other_scene_ptr, screen=types.SimpleNamespace(areas=[other_scene]))])
        ctx = types.SimpleNamespace(scene=self.scene, window_manager=wm)
        ns['_apply_view_display'](ctx, self.s)
        for area in (first, second):
            self.assertEqual(area.spaces.active.shading.type, 'SOLID')
            self.assertTrue(area.spaces.active.shading.show_xray)
            self.assertEqual(area.spaces.active.shading.xray_alpha, .27)
            self.assertEqual(area.redraws, 1)
        self.assertEqual(other_scene.spaces.active.shading.type, 'WIREFRAME')
        self.assertEqual(other_scene.redraws, 0)


if __name__ == '__main__':
    unittest.main()
