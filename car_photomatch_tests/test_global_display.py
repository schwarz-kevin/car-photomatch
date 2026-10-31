"""Regression coverage for photo-only global display after v0.4.10."""
import ast
import pathlib
import types
import unittest

ADDON = pathlib.Path(__file__).resolve().parents[1] / 'car_photomatch' / '__init__.py'
tree = ast.parse(ADDON.read_text(encoding='utf8'))
helper_names = {'_apply_photo_display', '_camera_reference'}
nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef)
         and node.name in helper_names]
ns = {}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ADDON), 'exec'), ns)


class FakeCameraData:
    def __init__(self, images=(), lens=55.):
        self.background_images = [types.SimpleNamespace(image=i, alpha=.9, display_depth='BACK') for i in images]
        self.show_background_images = True
        self.lens = lens

    def as_pointer(self):
        return id(self)


class FakeCamera:
    type = 'CAMERA'

    def __init__(self, name, data):
        self.name, self.data = name, data
        self.matrix_world = ('pose', name)


class PhotoOnlyDisplayTests(unittest.TestCase):
    def setUp(self):
        old_image = types.SimpleNamespace(name='old.png')
        new_image = types.SimpleNamespace(name='new.png')
        rim_image = types.SimpleNamespace(name='rim.png')
        self.old = FakeCamera('old', FakeCameraData([old_image]))
        self.new = FakeCamera('new', FakeCameraData([new_image]))
        self.rim = FakeCamera('rim', FakeCameraData([rim_image]))
        self.no_image = FakeCamera('empty', FakeCameraData())
        self.scene = types.SimpleNamespace(objects=[self.old, self.new, self.rim, self.no_image,
                                                    types.SimpleNamespace(type='MESH', name='CAR')])
        self.s = types.SimpleNamespace(opacity=.37, photo_depth='FRONT', show_camera_photo=True)

    def test_photo_controls_reach_old_new_and_rim_cameras_without_changing_pose_lens(self):
        ns['_apply_photo_display'](self.scene, self.s)
        for cam in [self.old, self.new, self.rim]:
            bg = cam.data.background_images[0]
            self.assertEqual(bg.alpha, .37)
            self.assertEqual(bg.display_depth, 'FRONT')
            self.assertTrue(cam.data.show_background_images)
            self.assertEqual(cam.matrix_world, ('pose', cam.name))
            self.assertEqual(cam.data.lens, 55.)

    def test_switching_photo_behind_model_and_hiding_reference(self):
        self.s.photo_depth = 'BACK'
        self.s.show_camera_photo = False
        ns['_apply_photo_display'](self.scene, self.s)
        self.assertTrue(all(not cam.data.show_background_images for cam in (self.old, self.new, self.rim)))
        self.assertTrue(all(cam.data.background_images[0].display_depth == 'BACK' for cam in (self.old, self.new, self.rim)))

    def test_blank_camera_unchanged(self):
        self.s.show_camera_photo = False
        ns['_apply_photo_display'](self.scene, self.s)
        self.assertTrue(self.no_image.data.show_background_images)

    def test_existing_camera_references_preserved(self):
        self.assertEqual(ns['_camera_reference'](self.old).name, 'old.png')

    def test_no_viewport_shading_or_object_display_writes(self):
        src = ADDON.read_text(encoding='utf8')
        for disallowed in ('space.shading.', '.shading.type =', '.shading.show_xray =',
                           'car_pm.display_preset', 'model_in_front', '_apply_view_display',
                           'model_opacity', "layout.prop(s, 'use_xray')"):
            self.assertNotIn(disallowed, src)
        self.assertNotIn('rim_pm.restore_solid', (ADDON.parent/'rim_mode.py').read_text())

    def test_panel_only_exposes_photo_controls(self):
        src=ADDON.read_text(encoding='utf8')
        draw = src.split('def _draw_global_display(',1)[1].split('class CARPM_PT_ViewDisplay(',1)[0]
        for required in ("'opacity'", "'photo_depth'", "'show_camera_photo'"):
            self.assertIn(required, draw)
        for forbidden in ('use_xray', 'model_opacity', 'view_shading', 'model_in_front', 'display_preset'):
            self.assertNotIn(forbidden, draw)


if __name__ == '__main__':
    unittest.main()
