"""Blender-free behavioral tests of the actual new-match helper via stub objects."""
import ast
import pathlib
import types
import unittest


ADDON_SOURCE = pathlib.Path(__file__).resolve().parents[1] / 'car_photomatch' / '__init__.py'
module_ast = ast.parse(ADDON_SOURCE.read_text(encoding='utf-8'))
helper_ast = next(n for n in module_ast.body if isinstance(n, ast.FunctionDef)
                  and n.name == '_begin_new_photomatch')
helper_code = compile(ast.Module(body=[helper_ast], type_ignores=[]), str(ADDON_SOURCE), 'exec')


class FakeCameraData:
    def __init__(self):
        self.type = 'PERSP'
        self.lens = 53.
        self.sensor_width = 36.
        self.sensor_height = 24.
        self.sensor_fit = 'AUTO'
        self.shift_x = 0.03
        self.shift_y = -0.01
        self.clip_start = 0.01
        self.clip_end = 2000.
        self.show_background_images = True
        self.background_images = []
        self.users = 0


class FakeCamera:
    def __init__(self, name, data):
        self.name, self.type, self.data = name, 'CAMERA', data
        self.matrix_world = [[1, 0], [0, 1]]


class FakeCameras:
    def __init__(self):
        self.items = []

    def new(self, name):
        camera = FakeCameraData()
        self.items.append(camera)
        return camera

    def remove(self, item):
        self.items.remove(item)


class FakeObjects:
    def __init__(self):
        self.items = []

    def new(self, name, data):
        obj = FakeCamera(name, data)
        data.users += 1
        self.items.append(obj)
        return obj

    def remove(self, obj, do_unlink=False):
        self.items.remove(obj)
        obj.data.users -= 1


class FakeObjectsInCollection:
    def __init__(self):
        self.items = []

    def link(self, obj):
        self.items.append(obj)


class FakePairs(list):
    def clear(self):
        super().clear()


class NewMatchTests(unittest.TestCase):
    def setUp(self):
        self.cameras = FakeCameras()
        self.objects = FakeObjects()
        env = {'bpy': types.SimpleNamespace(data=types.SimpleNamespace(
            cameras=self.cameras, objects=self.objects))}
        exec(helper_code, env)
        self.begin = env['_begin_new_photomatch']
        self.original_data = FakeCameraData()
        self.original_data.background_images = ['original photo']
        self.original = FakeCamera('Solved Camera', self.original_data)
        self.photo = object()
        self.scene = types.SimpleNamespace(
            camera=self.original,
            collection=types.SimpleNamespace(objects=FakeObjectsInCollection()))
        self.pairs = FakePairs([
            types.SimpleNamespace(object='car_mesh', local_point=(.1, .2, .3),
                                  name='Front Wheel', has_3d=True, has_2d=True,
                                  uv=(.25, .7), weight=2.),
            types.SimpleNamespace(object='car_mesh', local_point=(.5, .6, .7),
                                  name='Rear Wheel', has_3d=True, has_2d=True,
                                  uv=(.75, .2), weight=1.),
        ])
        self.settings = types.SimpleNamespace(
            camera=self.original, image=self.photo, pairs=self.pairs,
            last_background_name='car.jpg', has_solution=True,
            rms_px=0.72, active_pair=1)
        self.image_space = types.SimpleNamespace(image=self.photo)
        self.unrelated_space = types.SimpleNamespace(image='other picture')

    def check_old_preserved(self, new_camera):
        self.assertIsNot(new_camera, self.original)
        self.assertIsNot(new_camera.data, self.original_data)
        self.assertEqual(self.original.data.lens, 53.)
        self.assertEqual(self.original.data.background_images, ['original photo'])
        self.assertFalse(new_camera.data.show_background_images)
        self.assertEqual(new_camera.data.background_images, [])
        self.assertEqual(new_camera.data.lens, 53.)
        new_camera.data.lens = 35.
        self.assertEqual(self.original.data.lens, 53.)
        self.assertEqual(new_camera.data.shift_x, .03)
        self.assertEqual(new_camera.matrix_world, self.original.matrix_world)
        self.assertIs(self.scene.camera, new_camera)
        self.assertIs(self.settings.camera, new_camera)
        self.assertIsNone(self.settings.image)
        self.assertEqual(self.settings.last_background_name, '')
        self.assertFalse(self.settings.has_solution)
        self.assertEqual(self.settings.rms_px, 0.)
        self.assertEqual(self.settings.active_pair, 0)
        self.assertIsNone(self.image_space.image)
        self.assertEqual(self.unrelated_space.image, 'other picture')
        self.assertEqual(len(self.scene.collection.objects.items), 1)

    def test_reuse_3d_landmarks(self):
        new_camera = self.begin(self.scene, self.settings, True,
                                [self.image_space, self.unrelated_space])
        self.check_old_preserved(new_camera)
        self.assertEqual(len(self.pairs), 2)
        self.assertEqual(self.pairs[0].name, 'Front Wheel')
        self.assertEqual(self.pairs[0].object, 'car_mesh')
        self.assertEqual(self.pairs[0].local_point, (.1, .2, .3))
        self.assertEqual(self.pairs[0].weight, 2.)
        for point in self.pairs:
            self.assertTrue(point.has_3d)
            self.assertFalse(point.has_2d)
            self.assertEqual(point.uv, (0., 0.))

    def test_clear_all_landmarks(self):
        new_camera = self.begin(self.scene, self.settings, False,
                                [self.image_space, self.unrelated_space])
        self.check_old_preserved(new_camera)
        self.assertEqual(len(self.pairs), 0)


if __name__ == '__main__':
    unittest.main()
