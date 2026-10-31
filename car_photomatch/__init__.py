# SPDX-License-Identifier: GPL-3.0-or-later
"""Car PhotoMatch - perspective camera matching for existing car models.

Designed for Blender 5.2. Enable the extension, then open the PhotoMatch tab
in the 3D View and in an Image Editor (View mode).
"""
bl_info = {
    'name': 'Car PhotoMatch',
    'author': 'Car PhotoMatch Project',
    'version': (0, 4, 12),
    'blender': (5, 2, 0),
    'location': '3D View and Image Editor > Sidebar > PhotoMatch',
    'description': 'Automotive camera matching plus an experimental rim photo calibration workflow',
    'category': 'Camera',
}

import bpy
import blf
import gpu
import math
import numpy as np
from mathutils import Vector, Matrix
from bpy.props import (
    BoolProperty, CollectionProperty, FloatProperty, FloatVectorProperty,
    IntProperty, PointerProperty, StringProperty, EnumProperty,
)
from bpy_extras.io_utils import ImportHelper
from bpy_extras.view3d_utils import (
    region_2d_to_origin_3d, region_2d_to_vector_3d,
    location_3d_to_region_2d,
)
from bpy_extras.object_utils import world_to_camera_view
from gpu_extras.batch import batch_for_shader

from . import solver


_VIEW_HANDLE = None
_IMAGE_HANDLE = None


def _invalidate(self, context):
    if context and context.scene:
        context.scene.car_pm.has_solution = False


def _apply_photo_display(scene, settings):
    """Apply one set of scene-wide photo controls to ALL camera photos.

    This also covers older v0.2 cameras (which were not tagged as managed).
    It changes display only; image identity, camera lens and camera pose remain
    untouched. Only camera objects in the current scene are considered.
    """
    seen_data = set()
    for obj in scene.objects:
        if obj.type != 'CAMERA' or obj.data is None:
            continue
        data = obj.data
        key = data.as_pointer()
        if key in seen_data or not len(data.background_images):
            continue
        seen_data.add(key)
        data.show_background_images = settings.show_camera_photo
        for bg in data.background_images:
            if bg.image is not None:
                bg.alpha = settings.opacity
                bg.display_depth = settings.photo_depth


def _photo_display_changed(self, context):
    if context and context.scene:
        _apply_photo_display(context.scene, self)
        _redraw(context)


def _opacity_changed(self, context):
    # Existing v0.2 opacity values and stored scenes use the same property.
    _photo_display_changed(self, context)


def _redraw(context=None):
    if context is None:
        context = bpy.context
    screen = getattr(context, 'screen', None)
    if screen:
        for area in screen.areas:
            if area.type in {'VIEW_3D', 'IMAGE_EDITOR'}:
                area.tag_redraw()


def _active_pair(settings):
    i = settings.active_pair
    return settings.pairs[i] if 0 <= i < len(settings.pairs) else None


def _point_world(pair):
    return pair.object.matrix_world @ Vector(pair.local_point) if pair.object else Vector(pair.world_point)


def _image_dims(settings):
    if settings.image is None:
        return None
    w, h = settings.image.size
    return (int(w), int(h)) if w > 0 and h > 0 else None


def _select_camera(scene, settings):
    cam = settings.camera or scene.camera
    if not cam or cam.type != 'CAMERA':
        data = bpy.data.cameras.new('PhotoMatch Camera')
        cam = bpy.data.objects.new('PhotoMatch Camera', data)
        scene.collection.objects.link(cam)
        # A rough initial pose; DLT can initialize automatically from distributed points.
        cam.location = (6., -9., 3.5)
        target = Vector((0., 0., .8))
        cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.lens = 50.
    cam.data.type = 'PERSP'
    scene.camera = cam
    settings.camera = cam
    return cam


def _setup_reference(scene, settings):
    if settings.image is None:
        raise ValueError('Load a reference image first')
    cam = _select_camera(scene, settings)
    cam.data.show_background_images = settings.show_camera_photo
    # Only remove a previous add-on-owned image, preserving user background images.
    if settings.last_background_name:
        for bg in list(cam.data.background_images):
            if bg.image and bg.image.name == settings.last_background_name:
                cam.data.background_images.remove(bg)
    bg = cam.data.background_images.new()
    bg.image = settings.image
    bg.alpha = settings.opacity
    bg.display_depth = settings.photo_depth
    bg.frame_method = 'STRETCH'
    settings.last_background_name = settings.image.name
    return cam


class CARPM_Pair(bpy.types.PropertyGroup):
    name: StringProperty(name='Name', default='Landmark', update=_invalidate)
    object: PointerProperty(type=bpy.types.Object, name='Mesh Object', update=_invalidate)
    local_point: FloatVectorProperty(name='Object-local Point', size=3, precision=5, update=_invalidate)
    world_point: FloatVectorProperty(name='Free World Point', size=3, precision=5, update=_invalidate)
    uv: FloatVectorProperty(name='Photo UV', size=2, min=0., max=1., precision=5, update=_invalidate,
                            description='Normalized photo position; origin at bottom-left')
    has_3d: BoolProperty(name='Has 3D Landmark', default=False, update=_invalidate)
    has_2d: BoolProperty(name='Has Photo Landmark', default=False, update=_invalidate)
    enabled: BoolProperty(name='Enabled', default=True, update=_invalidate)
    weight: FloatProperty(name='Weight', default=1., min=.05, max=20., update=_invalidate)


class CARPM_Settings(bpy.types.PropertyGroup):
    image: PointerProperty(type=bpy.types.Image, name='Photo')
    camera: PointerProperty(type=bpy.types.Object, name='Camera')
    model_collection: PointerProperty(type=bpy.types.Collection, name='Car Collection',
                                      description='Optional car meshes for landmark picking')
    pairs: CollectionProperty(type=CARPM_Pair)
    active_pair: IntProperty(name='Active Pair', default=0, min=0)
    # All display settings below are per-scene, NOT per-camera. Every camera
    # with a background image in this scene receives the same photo settings.
    opacity: FloatProperty(name='Photo Opacity', default=.6, min=0., max=1., update=_opacity_changed)
    photo_depth: EnumProperty(name='Photo Placement', items=[
        ('FRONT', 'Photo Over Model', 'Place the reference image in front of 3D geometry'),
        ('BACK', 'Photo Behind Model', 'Place the reference image behind 3D geometry')],
        default='FRONT', update=_photo_display_changed)
    show_camera_photo: BoolProperty(name='Show Photo', default=True, update=_photo_display_changed)
    lock_lens: BoolProperty(name='Lock Focal Length', default=False)
    huber_px: FloatProperty(name='Outlier Threshold (px)', default=12., min=1., max=250.)
    max_iterations: IntProperty(name='Solver Iterations', default=80, min=10, max=200)
    show_markers: BoolProperty(name='Show Landmark Overlays', default=True)
    show_errors: BoolProperty(name='Show Reprojection Errors', default=True)
    reuse_3d_landmarks: BoolProperty(
        name='Reuse 3D Landmarks', default=True,
        description='Keep 3D point coordinates when starting a new match, but clear all photo positions')
    has_solution: BoolProperty(name='Has Current Solution', default=False)
    rms_px: FloatProperty(name='RMS Reprojection Error (px)', default=0.)
    last_background_name: StringProperty(name='Reference Ownership Tag', default='')


class CARPM_UL_Pairs(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item, 'enabled', text='')
        row.prop(item, 'name', text='', emboss=False, icon='EMPTY_AXIS')
        row.label(text=('3D' if item.has_3d else '--') + ' / ' + ('2D' if item.has_2d else '--'))


class CARPM_OT_LoadPhoto(bpy.types.Operator, ImportHelper):
    bl_idname = 'car_pm.load_photo'
    bl_label = 'Load Reference Photo'
    bl_description = 'Load a photo, set the render aspect, and create a camera background'
    bl_options = {'REGISTER', 'UNDO'}
    filter_glob: StringProperty(default='*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.webp;*.exr', options={'HIDDEN'})

    def execute(self, context):
        settings = context.scene.car_pm
        try:
            image = bpy.data.images.load(self.filepath, check_existing=True)
            if image.size[0] <= 0 or image.size[1] <= 0:
                raise ValueError('Image has invalid dimensions')
            settings.image = image
            context.scene.render.resolution_x = image.size[0]
            context.scene.render.resolution_y = image.size[1]
            context.scene.render.resolution_percentage = 100
            context.scene.render.pixel_aspect_x = 1.
            context.scene.render.pixel_aspect_y = 1.
            camera = _setup_reference(context.scene, settings)
            _apply_photo_display(context.scene, settings)
            for area in context.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = image
            if context.area.type == 'VIEW_3D':
                context.area.spaces.active.region_3d.view_perspective = 'CAMERA'
            settings.has_solution = False
            _redraw(context)
            self.report({'INFO'}, f'Loaded {image.name}; camera {camera.name}; {image.size[0]}x{image.size[1]}')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class CARPM_OT_SetupCamera(bpy.types.Operator):
    bl_idname = 'car_pm.setup_camera'
    bl_label = 'Setup / Refresh Camera Overlay'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            _setup_reference(context.scene, context.scene.car_pm)
            if context.area.type == 'VIEW_3D':
                context.area.spaces.active.region_3d.view_perspective = 'CAMERA'
        except Exception as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}
        _redraw(context)
        return {'FINISHED'}



def _begin_new_photomatch(scene, settings, keep_3d_landmarks, image_spaces=()):
    """Archive the previous result as an untouched camera and reset active work.

    Deliberately does not save prior photo point pairs: the old camera's solved
    transform, camera datablock and background photo are sufficient for viewing
    or rendering the previous match. Each new camera gets its own data block.
    """
    previous = settings.camera or scene.camera
    # Never share camera data with the old camera; lens/background changes must
    # not affect a previous solve.
    data = bpy.data.cameras.new('PhotoMatch Camera')
    try:
        if previous and previous.type == 'CAMERA':
            source = previous.data
            for attr in ('lens', 'sensor_width', 'sensor_height', 'sensor_fit',
                         'shift_x', 'shift_y', 'clip_start', 'clip_end'):
                setattr(data, attr, getattr(source, attr))
        data.type = 'PERSP'
        data.show_background_images = False
        cam = bpy.data.objects.new('PhotoMatch Camera', data)
        try:
            scene.collection.objects.link(cam)
        except Exception:
            bpy.data.objects.remove(cam, do_unlink=True)
            raise
        if previous and previous.type == 'CAMERA':
            cam.matrix_world = previous.matrix_world.copy()
        else:
            cam.location = (6., -9., 3.5)
            target = Vector((0., 0., .8))
            cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
            cam.data.lens = 50.
    except Exception:
        if data.users == 0:
            bpy.data.cameras.remove(data)
        raise

    old_image = settings.image
    # The previous camera and its photo remain untouched. Reset ONLY the
    # per-scene active matching state and the current image display.
    scene.camera = cam
    settings.camera = cam
    settings.image = None
    settings.last_background_name = ''
    settings.has_solution = False
    settings.rms_px = 0.
    if keep_3d_landmarks:
        for pair in settings.pairs:
            pair.has_2d = False
            pair.uv = (0., 0.)
    else:
        settings.pairs.clear()
    settings.active_pair = 0

    for space in image_spaces:
        if old_image is not None and space.image == old_image:
            space.image = None
    return cam


class CARPM_OT_NewPhotomatch(bpy.types.Operator):
    bl_idname = 'car_pm.new_photomatch'
    bl_label = 'New Photomatch'
    bl_description = ('Keep the previous camera and its photo; create a new '
                      'independent camera and reset matching points')
    bl_options = {'REGISTER', 'UNDO'}

    keep_3d_landmarks: BoolProperty(
        name='Keep 3D Landmarks', default=True,
        description='Retain the 3D positions, but clear all photo coordinates')

    def execute(self, context):
        settings = context.scene.car_pm
        try:
            spaces = [area.spaces.active for area in context.screen.areas
                      if area.type == 'IMAGE_EDITOR'] if context.screen else []
            new_camera = _begin_new_photomatch(
                context.scene, settings, self.keep_3d_landmarks, spaces)
            _apply_photo_display(context.scene, settings)
            # Keep the current viewport on the newly created camera.
            if context.area and context.area.type == 'VIEW_3D':
                context.area.spaces.active.region_3d.view_perspective = 'CAMERA'
            _redraw(context)
            message = ('3D landmarks kept; photo positions cleared' if self.keep_3d_landmarks
                       else 'All landmarks cleared')
            self.report({'INFO'}, f'{new_camera.name} ready. {message}.')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, f'Unable to create new photomatch: {exc}')
            return {'CANCELLED'}


def _camera_reference(camera):
    if not camera or camera.type != 'CAMERA':
        return None
    # Newest background image is the reference applied by this extension.
    return next((bg.image for bg in reversed(camera.data.background_images)
                 if bg.image is not None), None)


class CARPM_OT_ActivateCamera(bpy.types.Operator):
    bl_idname = 'car_pm.activate_camera'
    bl_label = 'View Selected Camera'
    bl_description = ('Switch to the selected photo camera and restore its photo aspect ratio; '
                      'existing camera transforms and focal lengths remain unchanged')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        s = scene.car_pm
        cam = s.camera
        if not cam or cam.type != 'CAMERA' or cam.name not in scene.objects:
            self.report({'ERROR'}, 'Choose a camera belonging to the current scene')
            return {'CANCELLED'}
        scene.camera = cam
        image = _camera_reference(cam)
        s.image = image
        s.last_background_name = image.name if image else ''
        if image and image.size[0] > 0 and image.size[1] > 0:
            scene.render.resolution_x = image.size[0]
            scene.render.resolution_y = image.size[1]
            scene.render.resolution_percentage = 100
            scene.render.pixel_aspect_x = 1.
            scene.render.pixel_aspect_y = 1.
        _apply_photo_display(scene, s)
        if context.screen:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
                elif area.type == 'IMAGE_EDITOR' and image:
                    area.spaces.active.image = image
        _redraw(context)
        self.report({'INFO'}, f'Viewing {cam.name}; previous matching points are not restored')
        return {'FINISHED'}


class CARPM_OT_ApplyGlobalDisplay(bpy.types.Operator):
    bl_idname = 'car_pm.apply_global_display'
    bl_label = 'Apply Display to All Cameras'
    bl_description = ('Synchronize photo placement and opacity on every camera '
                      'with a reference background in this scene, including old cameras')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.car_pm
        _apply_photo_display(context.scene, s)
        _redraw(context)
        self.report({'INFO'}, 'Reference photo settings applied to all cameras')
        return {'FINISHED'}


class CARPM_OT_PackImage(bpy.types.Operator):
    bl_idname = 'car_pm.pack_image'
    bl_label = 'Pack Photo into .blend'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        img = context.scene.car_pm.image
        if not img:
            self.report({'ERROR'}, 'No reference image loaded'); return {'CANCELLED'}
        try:
            img.pack()
        except Exception as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}
        self.report({'INFO'}, 'Photo packed into the Blender file')
        return {'FINISHED'}


class CARPM_OT_AddPair(bpy.types.Operator):
    bl_idname = 'car_pm.add_pair'
    bl_label = 'Add Landmark Pair'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.car_pm
        p = settings.pairs.add()
        p.name = f'Point {len(settings.pairs):02d}'
        settings.active_pair = len(settings.pairs) - 1
        settings.has_solution = False
        _redraw(context)
        return {'FINISHED'}


class CARPM_OT_RemovePair(bpy.types.Operator):
    bl_idname = 'car_pm.remove_pair'
    bl_label = 'Remove Landmark Pair'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        settings = context.scene.car_pm
        if 0 <= settings.active_pair < len(settings.pairs):
            settings.pairs.remove(settings.active_pair)
            settings.active_pair = max(0, min(settings.active_pair, len(settings.pairs)-1))
            settings.has_solution = False
            _redraw(context)
        return {'FINISHED'}


class CARPM_OT_CursorPoint(bpy.types.Operator):
    bl_idname = 'car_pm.cursor_point'
    bl_label = 'Use 3D Cursor as Landmark'
    bl_description = 'For wheel centers or other points away from mesh surfaces'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = _active_pair(context.scene.car_pm)
        if not p:
            self.report({'ERROR'}, 'Add a pair first'); return {'CANCELLED'}
        p.object = None
        p.world_point = context.scene.cursor.location
        p.has_3d = True
        _redraw(context)
        return {'FINISHED'}


class CARPM_OT_ObjectOrigin(bpy.types.Operator):
    bl_idname = 'car_pm.object_origin'
    bl_label = 'Use Active Object Origin'
    bl_description = 'Useful when individual wheel objects have origins at the axle center'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        p = _active_pair(context.scene.car_pm)
        obj = context.active_object
        if not p or not obj:
            self.report({'ERROR'}, 'Select an object and add a pair first'); return {'CANCELLED'}
        p.object = obj
        p.local_point = (0., 0., 0.)
        p.has_3d = True
        _redraw(context)
        return {'FINISHED'}


def _in_collection(obj, collection):
    if not collection:
        return True
    return obj.name in {candidate.name for candidate in collection.all_objects}


class CARPM_OT_Pick3D(bpy.types.Operator):
    bl_idname = 'car_pm.pick_3d'
    bl_label = 'Pick Point on 3D Model'
    bl_description = 'Click a mesh surface in the 3D View to assign the active pair 3D location'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'

    def invoke(self, context, event):
        if _active_pair(context.scene.car_pm) is None:
            self.report({'ERROR'}, 'Add a point pair first'); return {'CANCELLED'}
        self._area = context.area
        self._window_region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
        if self._window_region is None:
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        context.area.header_text_set('PhotoMatch: click the car mesh to set 3D point | Esc to cancel')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._area.header_text_set(None); return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            region = self._window_region
            x, y = event.mouse_x - region.x, event.mouse_y - region.y
            if not (0 <= x < region.width and 0 <= y < region.height):
                return {'RUNNING_MODAL'}
            rv3d = self._area.spaces.active.region_3d
            origin = region_2d_to_origin_3d(region, rv3d, (x, y))
            direction = region_2d_to_vector_3d(region, rv3d, (x, y))
            hit, location, normal, face_index, obj, matrix = context.scene.ray_cast(
                context.evaluated_depsgraph_get(), origin, direction)
            if not hit or not obj:
                self.report({'WARNING'}, 'No mesh under cursor; try again')
                return {'RUNNING_MODAL'}
            obj = getattr(obj, 'original', obj)
            if not _in_collection(obj, context.scene.car_pm.model_collection):
                self.report({'WARNING'}, 'Hit is outside the chosen Car Collection; try again')
                return {'RUNNING_MODAL'}
            p = _active_pair(context.scene.car_pm)
            p.object = obj
            p.local_point = obj.matrix_world.inverted_safe() @ location
            p.has_3d = True
            self._area.header_text_set(None)
            _redraw(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}


class CARPM_OT_Pick2D(bpy.types.Operator):
    bl_idname = 'car_pm.pick_2d'
    bl_label = 'Pick Point on Photo'
    bl_description = 'Click the matching photo landmark in the Image Editor'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'IMAGE_EDITOR'

    def invoke(self, context, event):
        settings = context.scene.car_pm
        if not settings.image or not _active_pair(settings):
            self.report({'ERROR'}, 'Load a photo and add a pair first'); return {'CANCELLED'}
        self._area = context.area
        self._window_region = next((r for r in self._area.regions if r.type == 'WINDOW'), None)
        if self._window_region is None:
            return {'CANCELLED'}
        if self._area.spaces.active.image != settings.image:
            self._area.spaces.active.image = settings.image
        context.window_manager.modal_handler_add(self)
        self._area.header_text_set('PhotoMatch: click the matching landmark in the photograph | Esc to cancel')
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._area.header_text_set(None); return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            region = self._window_region
            x, y = event.mouse_x - region.x, event.mouse_y - region.y
            if not (0 <= x < region.width and 0 <= y < region.height):
                return {'RUNNING_MODAL'}
            uv = region.view2d.region_to_view(x, y)
            if not (0 <= uv[0] <= 1 and 0 <= uv[1] <= 1):
                self.report({'WARNING'}, 'Click inside the displayed photo')
                return {'RUNNING_MODAL'}
            p = _active_pair(context.scene.car_pm)
            p.uv = (uv[0], uv[1])
            p.has_2d = True
            self._area.header_text_set(None)
            _redraw(context)
            return {'FINISHED'}
        return {'PASS_THROUGH'}


def _frame_intrinsics(scene, camera, size):
    """Read exact lens-dependent scaling and principal point from Blender frame."""
    frame = camera.data.view_frame(scene=scene)
    low_x = min(p.x for p in frame)
    high_x = max(p.x for p in frame)
    low_y = min(p.y for p in frame)
    high_y = max(p.y for p in frame)
    z = abs(frame[0].z)
    w, h = size
    fx = w * z / (high_x - low_x)
    fy = h * z / (high_y - low_y)
    cx = w * (-low_x) / (high_x - low_x)
    cy = h * high_y / (high_y - low_y)  # top-left image origin
    return fx, fy, cx, cy


class CARPM_OT_Solve(bpy.types.Operator):
    bl_idname = 'car_pm.solve'
    bl_label = 'Solve Camera'
    bl_description = 'Optimize camera pose and optionally focal length against all complete landmarks'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        settings = scene.car_pm
        size = _image_dims(settings)
        if not size:
            self.report({'ERROR'}, 'Load a valid photo'); return {'CANCELLED'}
        cam = settings.camera or scene.camera
        if not cam or cam.type != 'CAMERA' or cam.data.type != 'PERSP':
            self.report({'ERROR'}, 'Choose a perspective camera'); return {'CANCELLED'}
        if cam.constraints:
            self.report({'ERROR'}, 'Remove/disable camera constraints before solving'); return {'CANCELLED'}
        pairs = [p for p in settings.pairs if p.enabled and p.has_2d and p.has_3d]
        if len(pairs) < 6:
            self.report({'ERROR'}, 'At least six complete enabled 3D/2D pairs required'); return {'CANCELLED'}
        try:
            points = np.array([list(_point_world(p)) for p in pairs], dtype=float)
            pixels = np.array([[p.uv[0] * size[0], (1.-p.uv[1]) * size[1]] for p in pairs], dtype=float)
            weights = np.array([p.weight for p in pairs], dtype=float)
            fx, fy, cx, cy = _frame_intrinsics(scene, cam, size)
            rot = np.array([list(r) for r in cam.matrix_world.to_quaternion().to_matrix()])
            C = np.array(cam.matrix_world.translation[:], dtype=float)
            result = solver.solve_camera(points, pixels, weights, C, rot, cam.data.lens,
                                         fx, fy, cx, cy, lock_lens=settings.lock_lens,
                                         huber_px=settings.huber_px,
                                         max_iterations=settings.max_iterations)
            cam.matrix_world = Matrix.Translation(Vector(result['center'].tolist())) @ Matrix(result['rotation'].tolist()).to_4x4()
            if not settings.lock_lens:
                cam.data.lens = result['lens']
            scene.camera = cam
            settings.camera = cam
            # Verify against Blender's own projection (not just numerical solver).
            errors = []
            for p, target in zip(pairs, pixels):
                projected = world_to_camera_view(scene, cam, _point_world(p))
                predicted = np.array([projected.x * size[0], (1.-projected.y) * size[1]])
                errors.append(float(np.linalg.norm(predicted - target)))
            settings.rms_px = math.sqrt(sum(v*v for v in errors) / len(errors))
            settings.has_solution = True
            _redraw(context)
            self.report({'INFO'}, f'Solved {len(pairs)} points | RMS {settings.rms_px:.2f}px | lens {cam.data.lens:.1f}mm')
            return {'FINISHED'}
        except (solver.SolveError, ValueError, ZeroDivisionError, np.linalg.LinAlgError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def _draw_lines(lines, color, shader):
    if not lines:
        return
    gpu.state.blend_set('ALPHA')
    shader.bind()
    shader.uniform_float('color', color)
    coordinates = [point for segment in lines for point in segment]
    batch_for_shader(shader, 'LINES', {'pos': coordinates}).draw(shader)
    gpu.state.blend_set('NONE')


def _cross(lines, pos, radius=6.):
    x, y = pos
    lines.extend([((x-radius, y), (x+radius, y)),
                  ((x, y-radius), (x, y+radius))])


def _label(pos, text, active=False):
    font = 0
    blf.size(font, 12)
    blf.color(font, 1., .92 if active else 1., .25 if active else 1., 1.)
    blf.position(font, pos[0]+9, pos[1]+5, 0)
    blf.draw(font, text)


def _draw_image_markers():
    context = bpy.context
    area = context.area
    region = context.region
    if not area or area.type != 'IMAGE_EDITOR' or not region or region.type != 'WINDOW':
        return
    s = context.scene.car_pm
    if not s.image or area.spaces.active.image != s.image or not s.show_markers:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    pairs = s.pairs
    source_lines, active_lines, residual_lines, prediction_lines = [], [], [], []
    cam = s.camera or context.scene.camera
    for i, pair in enumerate(pairs):
        if not pair.has_2d:
            continue
        pos = region.view2d.view_to_region(*pair.uv, clip=False)
        is_active = i == s.active_pair
        _cross(active_lines if is_active else source_lines, pos, radius=7. if is_active else 5.)
        _label(pos, str(i+1), active=is_active)
        if (s.show_errors and pair.has_3d and cam and cam.type == 'CAMERA'):
            view = world_to_camera_view(context.scene, cam, _point_world(pair))
            if view.z > 0:
                dest = region.view2d.view_to_region(view.x, view.y, clip=False)
                residual_lines.append((pos, dest))
                _cross(prediction_lines, dest, 4.)
    _draw_lines(residual_lines, (1., .32, .25, .9), shader)
    _draw_lines(prediction_lines, (.2, .9, 1., .9), shader)
    _draw_lines(source_lines, (1., .95, .2, 1.), shader)
    _draw_lines(active_lines, (1., .5, .1, 1.), shader)


def _draw_view_markers():
    context = bpy.context
    area = context.area
    region = context.region
    if not area or area.type != 'VIEW_3D' or not region or region.type != 'WINDOW':
        return
    s = context.scene.car_pm
    if not s.show_markers:
        return
    rv3d = area.spaces.active.region_3d
    if not rv3d:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    lines, selected = [], []
    for i, p in enumerate(s.pairs):
        if not p.has_3d:
            continue
        pos = location_3d_to_region_2d(region, rv3d, _point_world(p))
        if pos is None:
            continue
        _cross(selected if i == s.active_pair else lines, pos, 7. if i == s.active_pair else 5.)
        _label(pos, str(i+1), active=i == s.active_pair)
    _draw_lines(lines, (.9, .9, .2, 1.), shader)
    _draw_lines(selected, (1., .5, .1, 1.), shader)


def _draw_ui(layout, context, image_editor=False):
    s = context.scene.car_pm
    col = layout.column(align=True)
    col.label(text='Reference & Camera', icon='CAMERA_DATA')
    col.prop(s, 'reuse_3d_landmarks', text='Reuse 3D Landmarks on New Match')
    op = col.operator('car_pm.new_photomatch', text='New Photomatch', icon='ADD')
    op.keep_3d_landmarks = s.reuse_3d_landmarks
    col.operator('car_pm.load_photo', icon='FILE_IMAGE')
    if s.image:
        col.prop(s, 'image')
        dims = _image_dims(s)
        if dims:
            col.label(text=f'{dims[0]} x {dims[1]} pixels')
    col.prop(s, 'camera')
    col.operator('car_pm.activate_camera', text='View Selected Camera', icon='VIEW_CAMERA')
    col.operator('car_pm.setup_camera', icon='RESTRICT_VIEW_OFF')
    col.operator('car_pm.pack_image', icon='FILE_BLEND')
    layout.separator()
    layout.label(text='Landmark Pairs', icon='EMPTY_AXIS')
    row = layout.row()
    row.template_list('CARPM_UL_Pairs', '', s, 'pairs', s, 'active_pair', rows=5)
    buttons = row.column(align=True)
    buttons.operator('car_pm.add_pair', text='', icon='ADD')
    buttons.operator('car_pm.remove_pair', text='', icon='REMOVE')
    p = _active_pair(s)
    if p:
        box = layout.box()
        box.prop(p, 'name')
        box.label(text=f'3D: {"Set" if p.has_3d else "Missing"} / Photo: {"Set" if p.has_2d else "Missing"}')
        if image_editor:
            box.operator('car_pm.pick_2d', text='Click Corresponding Photo Point', icon='EYEDROPPER')
        else:
            box.operator('car_pm.pick_3d', text='Click Point on Car Mesh', icon='EYEDROPPER')
            row = box.row(align=True)
            row.operator('car_pm.cursor_point', text='3D Cursor')
            row.operator('car_pm.object_origin', text='Object Origin')
        if p.has_3d:
            box.label(text=(f'Object: {p.object.name}' if p.object else 'World-space point'))
        if p.has_2d:
            box.prop(p, 'uv', text='Photo UV')
        box.prop(p, 'weight')
    if not image_editor:
        layout.prop(s, 'model_collection')
    layout.separator()
    layout.label(text='Camera Solve', icon='TRACKING')
    layout.prop(s, 'lock_lens')
    layout.prop(s, 'huber_px')
    layout.operator('car_pm.solve', icon='CON_CAMERASOLVER', text='Solve Camera')
    if s.has_solution:
        layout.label(text=f'RMS Error: {s.rms_px:.2f} px', icon='CHECKMARK')
        cam = s.camera or context.scene.camera
        if cam and cam.type == 'CAMERA':
            layout.label(text=f'Focal Length: {cam.data.lens:.2f} mm')
    layout.prop(s, 'show_markers')
    layout.prop(s, 'show_errors')
    layout.label(text='Tip: use 6-12 distinct points')


def _draw_global_display(layout, context):
    """Only reference-photo controls. Blender owns all shading and X-Ray settings."""
    s = context.scene.car_pm
    layout.label(text='Global Reference Photo', icon='IMAGE_DATA')
    layout.label(text='All photomatch cameras in this scene')
    layout.prop(s, 'show_camera_photo', text='Show Reference Photo')
    col = layout.column(align=True)
    col.enabled = s.show_camera_photo
    col.prop(s, 'opacity', text='Photo Opacity', slider=True)
    col.prop(s, 'photo_depth', text='Photo Layer')
    layout.operator('car_pm.apply_global_display', text='Apply to All Cameras', icon='FILE_REFRESH')
    layout.label(text='Set Solid/Wire/Materials in Blender')


class CARPM_PT_ViewDisplay(bpy.types.Panel):
    bl_label = 'Reference Photo Display'
    bl_idname = 'CARPM_PT_view_display'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        _draw_global_display(self.layout, context)


class CARPM_PT_ImageDisplay(bpy.types.Panel):
    bl_label = 'Reference Photo Display'
    bl_idname = 'CARPM_PT_image_display'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        _draw_global_display(self.layout, context)


class CARPM_PT_View(bpy.types.Panel):
    bl_label = 'Car PhotoMatch'
    bl_idname = 'CARPM_PT_view'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'

    def draw(self, context):
        _draw_ui(self.layout, context, image_editor=False)


class CARPM_PT_CameraTune(bpy.types.Panel):
    bl_label = 'Camera Fine Tune'
    bl_idname = 'CARPM_PT_camera_tune'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'
    bl_parent_id = 'CARPM_PT_view'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        cam = context.scene.camera
        layout = self.layout
        if not cam or cam.type != 'CAMERA':
            layout.label(text='Activate a camera first')
            return
        layout.label(text=cam.name, icon='CAMERA_DATA')
        layout.prop(cam, 'location', text='Position')
        layout.prop(cam, 'rotation_euler', text='Rotation')
        layout.prop(cam.data, 'lens', text='Focal Length')
        layout.prop(cam.data, 'shift_x', text='Shift X')
        layout.prop(cam.data, 'shift_y', text='Shift Y')
        layout.label(text='Works with previously solved cameras')


class CARPM_PT_Image(bpy.types.Panel):
    bl_label = 'Car PhotoMatch'
    bl_idname = 'CARPM_PT_image'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'

    def draw(self, context):
        _draw_ui(self.layout, context, image_editor=True)


from . import rim_mode

CLASSES = (
    CARPM_Pair, CARPM_Settings, CARPM_UL_Pairs,
    CARPM_OT_LoadPhoto, CARPM_OT_SetupCamera, CARPM_OT_NewPhotomatch,
    CARPM_OT_ActivateCamera, CARPM_OT_ApplyGlobalDisplay,
    CARPM_OT_PackImage,
    CARPM_OT_AddPair, CARPM_OT_RemovePair, CARPM_OT_CursorPoint,
    CARPM_OT_ObjectOrigin, CARPM_OT_Pick3D, CARPM_OT_Pick2D,
    CARPM_OT_Solve, CARPM_PT_View, CARPM_PT_Image,
    CARPM_PT_ViewDisplay, CARPM_PT_ImageDisplay, CARPM_PT_CameraTune,
)


def register():
    global _VIEW_HANDLE, _IMAGE_HANDLE
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.car_pm = PointerProperty(type=CARPM_Settings)
    # Do not access bpy.data.scenes here: Blender restricts bpy.data during
    # extension registration (_RestrictData). Existing camera backgrounds are
    # synchronized when the user changes a global display setting, selects an
    # older match, or presses Apply to All Cameras.
    if not bpy.app.background:
        _VIEW_HANDLE = bpy.types.SpaceView3D.draw_handler_add(_draw_view_markers, (), 'WINDOW', 'POST_PIXEL')
        _IMAGE_HANDLE = bpy.types.SpaceImageEditor.draw_handler_add(_draw_image_markers, (), 'WINDOW', 'POST_PIXEL')
    rim_mode.register()


def unregister():
    rim_mode.unregister()
    global _VIEW_HANDLE, _IMAGE_HANDLE
    if _VIEW_HANDLE is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_VIEW_HANDLE, 'WINDOW')
        _VIEW_HANDLE = None
    if _IMAGE_HANDLE is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_IMAGE_HANDLE, 'WINDOW')
        _IMAGE_HANDLE = None
    del bpy.types.Scene.car_pm
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == '__main__':
    register()
