"""Regression for the _RestrictData Blender extension-enable crash (v0.3.0)."""
import ast
import pathlib
import types
import unittest

ADDON = pathlib.Path(__file__).resolve().parents[1] / 'car_photomatch' / '__init__.py'
source = ADDON.read_text(encoding='utf8')
tree = ast.parse(source)
register_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'register')
unregister_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'unregister')


class RestrictedData:
    def __getattr__(self, name):
        raise AttributeError(f"'_RestrictData' object has no attribute '{name}'")


class RegistrationTests(unittest.TestCase):
    def test_register_and_unregister_under_restricted_data(self):
        classes = [object(), object()]
        visited = []
        view_space = types.SimpleNamespace(
            draw_handler_add=lambda *a: ('view_handle',),
            draw_handler_remove=lambda *a: visited.append(('view_remove', a)))
        image_space = types.SimpleNamespace(
            draw_handler_add=lambda *a: ('image_handle',),
            draw_handler_remove=lambda *a: visited.append(('image_remove', a)))
        scene_type = type('FakeScene', (), {})
        bpy = types.SimpleNamespace(
            data=RestrictedData(),
            utils=types.SimpleNamespace(register_class=lambda c: visited.append(('register', c)),
                                        unregister_class=lambda c: visited.append(('unregister', c))),
            types=types.SimpleNamespace(Scene=scene_type, SpaceView3D=view_space,
                                        SpaceImageEditor=image_space),
            app=types.SimpleNamespace(background=False))
        ns = {'bpy': bpy, 'CLASSES': classes, 'PointerProperty': lambda type: 'fake_property',
              'CARPM_Settings': object(), '_draw_view_markers': lambda: None,
              '_draw_image_markers': lambda: None, '_VIEW_HANDLE': None, '_IMAGE_HANDLE': None, 'rim_mode': types.SimpleNamespace(register=lambda: visited.append(('rim_register', None)), unregister=lambda: visited.append(('rim_unregister', None)))}
        funcs = ast.Module(body=[register_fn, unregister_fn], type_ignores=[])
        exec(compile(funcs, str(ADDON), 'exec'), ns)
        ns['register']()
        self.assertEqual(scene_type.car_pm, 'fake_property')
        self.assertEqual(ns['_VIEW_HANDLE'], ('view_handle',))
        self.assertEqual(ns['_IMAGE_HANDLE'], ('image_handle',))
        self.assertEqual([v for k, v in visited if k == 'register'], classes)
        ns['unregister']()
        self.assertFalse(hasattr(scene_type, 'car_pm'))
        self.assertEqual([v for k, v in visited if k == 'unregister'], list(reversed(classes)))


if __name__ == '__main__':
    unittest.main()
