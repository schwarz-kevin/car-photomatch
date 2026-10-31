# SPDX-License-Identifier: GPL-3.0-or-later
"""Experimental Rim PhotoMatch tools, kept separate from the car point matcher."""

import math
import bpy
import numpy as np
import blf
import gpu
from mathutils import Matrix, Vector
from bpy.props import (BoolProperty, CollectionProperty, FloatProperty,
                       FloatVectorProperty, IntProperty, PointerProperty, EnumProperty)
from bpy_extras.io_utils import ImportHelper
from gpu_extras.batch import batch_for_shader

from . import rim_core, rim_guides
from . import _frame_intrinsics, _redraw

_RIM_DRAW_HANDLE = None


class RIMPM_Ellipse(bpy.types.PropertyGroup):
    coords: FloatVectorProperty(name='Detected ellipse (pixels)', size=5)
    score: FloatProperty(name='Edge confidence', min=0., max=1.)


class RIMPM_CameraSolution(bpy.types.PropertyGroup):
    center: FloatVectorProperty(name='Camera center', size=3)
    rotation: FloatVectorProperty(name='Camera rotation', size=9)
    rms: FloatProperty(name='Fit error (px)', default=0., min=0.)
    angle: FloatProperty(name='Face inclination', default=0.)


class RIMPM_Settings(bpy.types.PropertyGroup):
    image: PointerProperty(type=bpy.types.Image, name='Rim Photograph')
    camera: PointerProperty(type=bpy.types.Object, name='Rim Camera')
    rig_root: PointerProperty(type=bpy.types.Object, name='Rim Rig Root')
    roi_uv: FloatVectorProperty(name='Selection Bounds UV', size=4, default=(0., 0., 1., 1.))
    roi_valid: BoolProperty(name='Area Selected', default=False)
    candidates: CollectionProperty(type=RIMPM_Ellipse)
    candidate_index: IntProperty(name='Chosen Edge', default=0, min=0)
    solutions: CollectionProperty(type=RIMPM_CameraSolution)
    solution_index: IntProperty(name='Chosen Camera', default=0, min=0)
    # Kept for backwards compatibility and optional precision override only.
    # The normal workflow derives the diameter from known wheel geometry.
    edge_diameter_mm: FloatProperty(name='Exact Edge Diameter (mm)', default=500.,
                                   min=5., max=2500., precision=1,
                                   description='Optional measured diameter of the highlighted ring')
    override_edge_diameter: BoolProperty(name='Use Exact Diameter Override', default=False,
                                        description='Advanced: override automatic or estimated ring diameter for a measured value')
    nominal_diameter_in: FloatProperty(name='Nominal Rim Diameter (in)', default=19., min=8., max=40., precision=1)
    width_in: FloatProperty(name='Rim Width (in)', default=9.5, min=1., max=30., precision=1)
    circle_vertices: IntProperty(name='Guide Circle Vertices', default=48, min=6, max=512,
                                 description='Vertex count for generated rim guide circle meshes')
    fill_guide_faces: BoolProperty(name='Fill Rim Guide Circles', default=False,
                                   description='Create actual mesh faces on the generated rim circles, so they appear as filled surfaces in Solid shading; disabled creates editable edge loops')
    create_lug_guides: BoolProperty(name='Create Lug Guides', default=False,
                                    description='Generate circle mesh guides for the lug-hole pattern')
    lug_count: IntProperty(name='Bolt Pattern Count', default=5, min=3, max=12)
    pcd_mm: FloatProperty(name='PCD / Bolt Circle Diameter (mm)', default=114.3, min=20., max=400., precision=2,
                          description='Pitch circle diameter for the lug-hole centers')
    lug_diameter_mm: FloatProperty(name='Lug Hole Guide Diameter (mm)', default=14., min=1., max=80., precision=2,
                                   description='Diameter of each generated lug-hole guide circle')
    lug_circle_vertices: IntProperty(name='Lug Circle Vertices', default=24, min=6, max=256,
                                      soft_min=8, soft_max=64,
                                      description='Vertices PER lug-hole circle; all lug circles are combined into one editable mesh object')
    create_hub_guide: BoolProperty(name='Create ET / Hub Guide', default=False,
                                    description='Create a center-bore vertex circle at the axle mounting-face plane defined by wheel width and ET')
    offset_et_mm: FloatProperty(name='Offset ET (mm)', default=35., min=-200., max=200., precision=1,
                                 description='Positive ET: hub mounting face towards the wheel exterior (+Z); negative ET: inboard (-Z)')
    center_bore_mm: FloatProperty(name='Center Bore Diameter (mm)', default=66.6, min=5., max=250., precision=1,
                                  description='Physical center-hole diameter for the circular guide, independent of ET')
    photo_ring_type: EnumProperty(name='Detected Ring Type', default='MANUAL', items=[
        ('MANUAL', 'Other / Manual', 'Preserve the original manual front bead-seat Z offset'),
        ('FRONT_BEAD', 'Front Bead Seat', 'Selected photo ring is at the outboard tire bead seat'),
        ('REAR_BEAD', 'Rear Bead Seat', 'Selected photo ring is at the inboard tire bead seat'),
        ('FRONT_LIP', 'Front Outer Lip', 'Selected photo ring is the outer lip, beyond the front bead seat'),
        ('REAR_LIP', 'Rear Outer Lip', 'Selected photo ring is the rear lip, beyond the rear bead seat'),
        ('HUB_FACE', 'Hub Mounting Face', 'Selected circular edge is known to lie in the actual hub mounting plane'),
        ('CENTER_BORE', 'Center Bore', 'Selected photo edge is the center bore at the hub mounting plane'),
    ], description='Which physical rim feature corresponds to the detected photo ellipse?')
    lip_overhang_mm: FloatProperty(name='Lip to Bead Seat (mm)', default=12., min=0., max=150., precision=1,
                                    description='Axial distance from the selected outer lip to its tire bead seat; must be measured or estimated')
    front_bead_seat_z_mm: FloatProperty(name='Manual Front Bead Z (mm)',
                                        default=-12., min=-300., max=300., precision=1,
                                        description='Legacy/manual signed position of front tire bead seat relative to the detected photo ring at Z=0')
    lens_mm: FloatProperty(name='Assumed Focal Length (mm)', default=50., min=8., max=400., precision=1,
                           description='Needed because a single circular feature cannot determine unknown focal length')
    show_candidates: BoolProperty(name='Show Edge Candidates', default=True)
    show_roi: BoolProperty(name='Show Selected Area', default=True)


def _reset_candidates(s):
    s.candidates.clear()
    s.solutions.clear()
    s.candidate_index = 0
    s.solution_index = 0


def _image_dims(s):
    if s.image:
        w, h = s.image.size
        if w > 0 and h > 0:
            return int(w), int(h)
    return None


def _get_camera(scene, s):
    cam = s.camera
    if cam and cam.type == 'CAMERA' and cam.name in scene.objects:
        return cam
    # Only create when the user requests it; Blender restricts bpy.data during registration.
    data = bpy.data.cameras.new('Rim Match Camera')
    data.type = 'PERSP'
    data.lens = s.lens_mm
    data.clip_end = 1000.
    cam = bpy.data.objects.new('Rim Match Camera', data)
    scene.collection.objects.link(cam)
    s.camera = cam
    return cam


def _set_background(scene, s):
    cam = _get_camera(scene, s)
    # Camera is exclusively owned by Rim PhotoMatch. No modification to existing car cameras.
    cam.data.background_images.clear()
    bg = cam.data.background_images.new()
    bg.image = s.image
    bg.alpha = scene.car_pm.opacity
    bg.display_depth = scene.car_pm.photo_depth
    bg.frame_method = 'STRETCH'
    cam.data.show_background_images = scene.car_pm.show_camera_photo
    cam.data.lens = s.lens_mm
    scene.camera = cam
    return cam


class RIMPM_OT_LoadPhoto(bpy.types.Operator, ImportHelper):
    bl_idname = 'rim_pm.load_photo'
    bl_label = 'Load Rim Photograph'
    bl_description = 'Use a reference image with a dedicated camera; existing car match cameras are untouched'
    bl_options = {'REGISTER', 'UNDO'}
    filter_glob: bpy.props.StringProperty(default='*.png;*.jpg;*.jpeg;*.tif;*.tiff;*.bmp;*.webp', options={'HIDDEN'})

    def execute(self, context):
        s, scene = context.scene.rim_pm, context.scene
        try:
            image = bpy.data.images.load(self.filepath, check_existing=True)
            if not image.size[0] or not image.size[1]:
                raise ValueError('Invalid photo dimensions')
            s.image = image
            _reset_candidates(s)
            s.roi_valid = False
            scene.render.resolution_x = image.size[0]
            scene.render.resolution_y = image.size[1]
            scene.render.resolution_percentage = 100
            scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.
            cam = _set_background(scene, s)
            if context.screen:
                for area in context.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        area.spaces.active.image = image
                    elif area.type == 'VIEW_3D':
                        area.spaces.active.region_3d.view_perspective = 'CAMERA'
            _redraw(context)
            self.report({'INFO'}, f'Rim image: {image.name}; camera {cam.name}')
            return {'FINISHED'}
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class RIMPM_OT_PickArea(bpy.types.Operator):
    bl_idname = 'rim_pm.pick_area'
    bl_label = 'Draw Rim Selection Rectangle'
    bl_description = 'Drag a rough rectangle around the photographed rim in an Image Editor'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'IMAGE_EDITOR'

    def invoke(self, context, event):
        s = context.scene.rim_pm
        if not _image_dims(s):
            self.report({'ERROR'}, 'Load a Rim Photograph first')
            return {'CANCELLED'}
        self._area = context.area
        self._region = next((r for r in context.area.regions if r.type == 'WINDOW'), None)
        if self._region is None:
            return {'CANCELLED'}
        self._area.spaces.active.image = s.image
        self._dragging = False
        self._area.header_text_set('Rim PhotoMatch: drag around the full rim | ESC to cancel')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def _uv(self, event):
        r = self._region
        x, y = event.mouse_x - r.x, event.mouse_y - r.y
        if not (0 <= x <= r.width and 0 <= y <= r.height):
            return None
        uv = r.view2d.region_to_view(x, y)
        return tuple(np.clip(uv[:2], 0., 1.))

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._area.header_text_set(None)
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self._start = self._uv(event)
            if self._start is None:
                return {'RUNNING_MODAL'}
            self._dragging = True
            return {'RUNNING_MODAL'}
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE' and self._dragging:
            end = self._uv(event)
            if end is None:
                end = self._start
            x0, y0 = self._start
            x1, y1 = end
            s = context.scene.rim_pm
            w, h = _image_dims(s)
            if abs(x1-x0)*w < 45 or abs(y1-y0)*h < 45:
                self.report({'WARNING'}, 'Selection too small; drag around the entire rim')
                self._area.header_text_set(None)
                return {'CANCELLED'}
            s.roi_uv = (min(x0,x1), min(y0,y1), max(x0,x1), max(y0,y1))
            s.roi_valid = True
            _reset_candidates(s)
            self._area.header_text_set(None)
            _redraw(context)
            self.report({'INFO'}, 'Rim area selected; click Detect Rim Edges')
            return {'FINISHED'}
        return {'RUNNING_MODAL'} if self._dragging else {'PASS_THROUGH'}


def _read_pixels(image):
    w, h = image.size
    if max(w, h) > 16000 or w*h > 60_000_000:
        raise rim_core.RimSolveError('Image too large; resize to under 60 megapixels')
    n_channels = int(image.channels)
    buf = np.empty(w*h*n_channels, dtype=np.float32)
    image.pixels.foreach_get(buf)
    return np.flipud(buf.reshape(h, w, n_channels))


class RIMPM_OT_Detect(bpy.types.Operator):
    bl_idname = 'rim_pm.detect'
    bl_label = 'Detect Rim Edges'
    bl_description = 'Experimental, local gradient-based detection of possible circular boundaries'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.rim_pm
        dims = _image_dims(s)
        if not dims or not s.roi_valid:
            self.report({'ERROR'}, 'Load a photo and draw a rim area in Image Editor')
            return {'CANCELLED'}
        try:
            w, h = dims
            left, bottom, right, top = s.roi_uv
            roi = (left*w, (1.-top)*h, right*w, (1.-bottom)*h)
            image = _read_pixels(s.image)
            results = rim_core.detect_ellipse_candidates(image, roi=roi)
            _reset_candidates(s)
            for ellipse, score in results:
                item = s.candidates.add()
                item.coords = ellipse
                item.score = score
            _redraw(context)
            if not results:
                self.report({'WARNING'}, 'No strong elliptical edges detected; try a tighter crop or clearer photo')
                return {'CANCELLED'}
            self.report({'INFO'}, f'{len(results)} possible rim edges found. Choose the correct one.')
            return {'FINISHED'}
        except (rim_core.RimSolveError, ValueError, MemoryError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class RIMPM_OT_ManualPoints(bpy.types.Operator):
    bl_idname = 'rim_pm.manual_points'
    bl_label = 'Fallback: Pick 8 Rim Edge Points'
    bl_description = 'When automatic detection fails, click eight points around one known circular rim edge'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == 'IMAGE_EDITOR'

    def invoke(self, context, event):
        s = context.scene.rim_pm
        if not _image_dims(s):
            self.report({'ERROR'}, 'Load a Rim Photograph first')
            return {'CANCELLED'}
        self._area = context.area
        self._region = next((r for r in self._area.regions if r.type == 'WINDOW'), None)
        if self._region is None:
            return {'CANCELLED'}
        self._area.spaces.active.image = s.image
        self._points = []
        self._area.header_text_set('Rim PhotoMatch: pick eight points around ONE circular edge | ESC to cancel')
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._area.header_text_set(None)
            return {'CANCELLED'}
        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            region = self._region
            x, y = event.mouse_x-region.x, event.mouse_y-region.y
            if not (0 <= x < region.width and 0 <= y < region.height):
                return {'RUNNING_MODAL'}
            u, v = region.view2d.region_to_view(x, y)
            if not (0 <= u <= 1 and 0 <= v <= 1):
                self.report({'WARNING'}, 'Pick inside the photo')
                return {'RUNNING_MODAL'}
            s = context.scene.rim_pm
            w, h = _image_dims(s)
            self._points.append((u*w, (1.-v)*h))
            if len(self._points) == 8:
                self._area.header_text_set(None)
                try:
                    ellipse = rim_core.fit_ellipse(self._points)
                except rim_core.RimSolveError as exc:
                    self.report({'ERROR'}, str(exc))
                    return {'CANCELLED'}
                # Add manual candidate without destroying automatically found candidates.
                item = s.candidates.add()
                item.coords = ellipse
                item.score = 0.  # Not a machine-derived confidence score.
                s.candidate_index = len(s.candidates)-1
                s.solutions.clear()
                _redraw(context)
                self.report({'INFO'}, 'Manual circle fitted; check its overlay before solving')
                return {'FINISHED'}
            self._area.header_text_set(f'Rim PhotoMatch: {len(self._points)}/8 edge points | ESC to cancel')
            return {'RUNNING_MODAL'}
        return {'PASS_THROUGH'}


class RIMPM_OT_SwitchCandidate(bpy.types.Operator):
    bl_idname = 'rim_pm.switch_candidate'
    bl_label = 'Select Rim Edge Candidate'
    bl_options = {'REGISTER', 'UNDO'}
    offset: IntProperty(default=1)

    def execute(self, context):
        s = context.scene.rim_pm
        if not len(s.candidates):
            return {'CANCELLED'}
        s.candidate_index = (s.candidate_index+self.offset) % len(s.candidates)
        s.solutions.clear()
        _redraw(context)
        return {'FINISHED'}


def _finalize_rig_mesh(obj, parent):
    obj.parent = parent
    obj.hide_render = True
    obj.show_in_front = True
    # Do not force Blender to draw the entire object as WIRE regardless of
    # viewport shading. Edge-only guides remain visible as overlay wires,
    # while filled guide meshes display as ordinary solid geometry.
    obj.display_type = 'SOLID'
    # Object-level wire overlays override the user's viewport preference.
    # Rim PhotoMatch must not force their topology to be visible in Solid mode.
    obj.show_wire = False
    obj.show_all_edges = False
    return obj


# Recognize only add-on-created guide mesh objects. The repair command is
# intentionally restricted to Rim PhotoMatch construction objects, not the
# user's real rim mesh, shader nodes, modifiers or general Blender settings.
_RIM_GUIDE_PREFIXES = (
    'Photo Edge - measured circle', 'Bead Seat - nominal diameter',
    'Rear Width Reference - approximate', 'Wheel Axis', 'Face X Axis',
    'Face Y Axis', 'Lug Guide ', 'Lug Guides (',
    'Hub Mount Plane - Center Bore',
)


def _is_rim_guide_mesh(obj):
    root = getattr(obj, 'parent', None)
    return (getattr(obj, 'type', None) == 'MESH' and
            root is not None and root.name.startswith('RIM PM - Rig Root') and
            obj.name.startswith(_RIM_GUIDE_PREFIXES))


def _repair_rim_guide_wire(scene):
    """Disable forced wire overlays on legacy rig meshes only.

    Does not touch viewport shading, X-ray, user-model mesh data or materials.
    """
    count = 0
    for obj in scene.objects:
        if not _is_rim_guide_mesh(obj):
            continue
        obj.display_type = 'SOLID'
        obj.show_wire = False
        obj.show_all_edges = False
        count += 1
    return count


class RIMPM_OT_RepairGuideWire(bpy.types.Operator):
    bl_idname = 'rim_pm.repair_guide_wire'
    bl_label = 'Remove Forced Guide Wire Overlay'
    bl_description = ('Clear forced edge overlays on Rim PhotoMatch guides from older versions; '
                      'does not alter model materials or viewport shading')
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        count = _repair_rim_guide_wire(context.scene)
        _redraw(context)
        if count:
            self.report({'INFO'}, f'Fixed wire-overlay settings for {count} Rim PhotoMatch guide objects')
        else:
            self.report({'INFO'}, 'No legacy Rim PhotoMatch mesh guides found')
        return {'FINISHED'}


def _new_rig_circle_mesh(parent, collection, name, radius, z, segments=48, filled=False):
    segments = max(6, int(segments))
    mesh = bpy.data.meshes.new(name)
    verts = []
    edges = []
    for i in range(segments):
        angle = 2*math.pi*i/segments
        verts.append((radius*math.cos(angle), radius*math.sin(angle), z))
        edges.append((i, (i+1) % segments))
    mesh.from_pydata(verts, edges, [tuple(range(segments))] if filled else [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return _finalize_rig_mesh(obj, parent)


def _create_line_mesh(parent, collection, name, p1, p2):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(p1), tuple(p2)], [(0, 1)], [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return _finalize_rig_mesh(obj, parent)



def _create_lug_guides(parent, collection, count, pcd_radius, lug_radius, z, segments=24):
    """One mesh object containing independent circular edge loops for every lug."""
    verts, edges = rim_guides.lug_guide_mesh(count, pcd_radius, lug_radius, segments, z=z)
    name = f'Lug Guides ({count}x{pcd_radius * 2000.:g} PCD)'
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return _finalize_rig_mesh(obj, parent)


_HUB_GUIDE_ROLE = 'hub_mount_face'


def _effective_edge_diameter(s):
    return rim_guides.effective_photo_ring_diameter_mm(
        s.nominal_diameter_in, s.photo_ring_type,
        s.center_bore_mm, s.edge_diameter_mm, s.override_edge_diameter)


def _front_bead_z_mm(s):
    """Front bead seat relative to selected photo ring; ring stays at Z=0."""
    return rim_guides.photo_ring_front_bead_z_mm(
        s.width_in, s.offset_et_mm, s.photo_ring_type,
        s.lip_overhang_mm, s.front_bead_seat_z_mm)


def _hub_guide_z(s):
    """Local Z of the mounting plane; front/outboard is positive Z."""
    return rim_guides.mounting_face_z_m(
        s.width_in, s.offset_et_mm, _front_bead_z_mm(s))


def _sync_rig_reference_depths(root, s):
    """Move only generated reference circles and the axis when ring type changes.

    Important for existing v0.4.6 rigs: updating a hub guide must also update
    bead-seat visual guides, or they will contradict the mounting-plane circle.
    Preserve object identity, radius, XY coordinates and user-modeled objects.
    """
    front = _front_bead_z_mm(s) / 1000.0
    rear = front - s.width_in * .0254
    targets = {'Bead Seat - nominal diameter': front,
               'Rear Width Reference - approximate': rear}
    for obj in root.children:
        if obj.type != 'MESH':
            continue
        if obj.name in targets:
            for vert in obj.data.vertices:
                vert.co.z = targets[obj.name]
            obj.data.update()
        elif obj.name == 'Wheel Axis' and len(obj.data.vertices) == 2:
            obj.data.vertices[0].co.z = rear - .1
            obj.data.vertices[1].co.z = .1
            obj.data.update()


def _sync_rig_bead_circle_diameters(root, s):
    """Resize only the two generated nominal bead-seat circles."""
    radius = s.nominal_diameter_in * .0254 / 2.0
    for obj in root.children:
        if obj.type != 'MESH' or obj.name not in {'Bead Seat - nominal diameter', 'Rear Width Reference - approximate'}:
            continue
        for vert in obj.data.vertices:
            ang = math.atan2(vert.co.y, vert.co.x)
            vert.co.x = radius * math.cos(ang)
            vert.co.y = radius * math.sin(ang)
        obj.data.update()


def _sync_rig_photo_diameter(root, s):
    # Update only generated photo-ring and face-axis guides after recalibration.
    radius = _effective_edge_diameter(s)[0] / 2000.0
    for obj in root.children:
        if obj.type != 'MESH':
            continue
        if obj.name == 'Photo Edge - measured circle':
            # Keep topology and any filled face; resize the radial vertex loop.
            for vert in obj.data.vertices:
                ang = math.atan2(vert.co.y, vert.co.x)
                vert.co.x = radius * math.cos(ang)
                vert.co.y = radius * math.sin(ang)
            obj.data.update()
        elif obj.name == 'Face X Axis' and len(obj.data.vertices) == 2:
            obj.data.vertices[0].co.x = -radius
            obj.data.vertices[1].co.x = radius
            obj.data.update()
        elif obj.name == 'Face Y Axis' and len(obj.data.vertices) == 2:
            obj.data.vertices[0].co.y = -radius
            obj.data.vertices[1].co.y = radius
            obj.data.update()


def _update_hub_guide(root, collection, s):
    """Create or update a *single* center-bore edge-loop in the mounting plane.

    Root origin is the chosen photo ring (Z=0). No existing car geometry or
    photomatch cameras are changed. The mounting plane's radial contact extent
    is NOT determined by ET; this ring denotes the center bore instead.
    """
    z = _hub_guide_z(s)  # Validate measurements before changing any mesh.
    _sync_rig_reference_depths(root, s)
    _sync_rig_bead_circle_diameters(root, s)
    _sync_rig_photo_diameter(root, s)
    radius = s.center_bore_mm / 2000.
    segments = int(s.circle_vertices)
    name = f'Hub Mount Plane - Center Bore (ET {s.offset_et_mm:+g})'
    guide = next((obj for obj in root.children
                  if obj.type == 'MESH' and obj.get('rim_pm_role') == _HUB_GUIDE_ROLE), None)
    if guide is None:
        guide = _new_rig_circle_mesh(root, collection, name, radius, z,
                                     segments=segments, filled=False)
        guide['rim_pm_role'] = _HUB_GUIDE_ROLE
    else:
        mesh = guide.data
        mesh.clear_geometry()
        verts, edges = rim_guides.circle_edge_loop(radius, segments, z=z)
        mesh.from_pydata(verts, edges, [])
        mesh.update()
        guide.name = name
        guide.location = (0., 0., 0.)
        _finalize_rig_mesh(guide, root)
    guide['rim_pm_et_mm'] = s.offset_et_mm
    guide['rim_pm_center_bore_mm'] = s.center_bore_mm
    guide['rim_pm_front_bead_z_mm'] = _front_bead_z_mm(s)
    guide['rim_pm_photo_ring_type'] = s.photo_ring_type
    return guide


class RIMPM_OT_UpdateHubGuide(bpy.types.Operator):
    bl_idname = 'rim_pm.update_hub_guide'
    bl_label = 'Add / Update ET Hub Guide'
    bl_description = 'Update reference-ring depths and the center-bore circle at the calculated hub mounting plane'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s, scene = context.scene.rim_pm, context.scene
        root = s.rig_root
        if root is None or root.name not in scene.objects:
            self.report({'ERROR'}, 'Create Modeling Rig first')
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'WARNING'}, 'Switch to Object Mode before updating the guide')
            return {'CANCELLED'}
        group = next((col for col in root.users_collection), None)
        if group is None:
            self.report({'ERROR'}, 'Rim rig root must belong to a collection')
            return {'CANCELLED'}
        try:
            _update_hub_guide(root, group, s)
        except (ValueError, RuntimeError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        _redraw(context)
        self.report({'INFO'}, f'Hub mounting plane: local Z = {_hub_guide_z(s)*1000:.2f} mm')
        return {'FINISHED'}


class RIMPM_OT_UpdateRingGuides(bpy.types.Operator):
    bl_idname = 'rim_pm.update_ring_guides'
    bl_label = 'Update Ring Guides'
    bl_description = 'Update generated photo-circle and bead-seat reference guides to match the selected ring type and nominal size'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene, s = context.scene, context.scene.rim_pm
        root = s.rig_root
        if root is None or root.name not in scene.objects:
            self.report({'ERROR'}, 'Create Modeling Rig first')
            return {'CANCELLED'}
        if context.mode != 'OBJECT':
            self.report({'WARNING'}, 'Switch to Object Mode before updating guides')
            return {'CANCELLED'}
        try:
            _sync_rig_reference_depths(root, s)
            _sync_rig_bead_circle_diameters(root, s)
            _sync_rig_photo_diameter(root, s)
        except ValueError as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}
        _redraw(context)
        self.report({'INFO'}, 'Photo diameter and bead-seat guides updated; re-solve the camera if needed')
        return {'FINISHED'}


class RIMPM_OT_CreateRig(bpy.types.Operator):
    bl_idname = 'rim_pm.create_rig'
    bl_label = 'Create Dimensioned Rim Rig'
    bl_description = 'Create construction rings and center axis at the 3D cursor; does not modify existing models'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene, s = context.scene, context.scene.rim_pm
        if s.rig_root and s.rig_root.name in scene.objects:
            self.report({'WARNING'}, 'Rim rig already exists; select it or delete it before rebuilding')
            return {'CANCELLED'}
        group = bpy.data.collections.new('Rim PhotoMatch Construction Rig')
        scene.collection.children.link(group)
        root = bpy.data.objects.new('RIM PM - Rig Root (XY face)', None)
        group.objects.link(root)
        root.empty_display_type = 'CIRCLE'
        root.empty_display_size = .04
        root.location = scene.cursor.location.copy()
        edge_radius = _effective_edge_diameter(s)[0] / 2000.
        nominal_radius = s.nominal_diameter_in * .0254 / 2.
        depth = s.width_in*.0254
        front_bead_z = _front_bead_z_mm(s) / 1000.
        rear_bead_z = front_bead_z - depth
        segs = s.circle_vertices
        _new_rig_circle_mesh(root, group, 'Photo Edge - measured circle', edge_radius, 0.,
                             segments=segs, filled=s.fill_guide_faces)
        _new_rig_circle_mesh(root, group, 'Bead Seat - nominal diameter', nominal_radius, front_bead_z,
                             segments=segs, filled=s.fill_guide_faces)
        _new_rig_circle_mesh(root, group, 'Rear Width Reference - approximate', nominal_radius, rear_bead_z,
                             segments=segs, filled=s.fill_guide_faces)
        _create_line_mesh(root, group, 'Wheel Axis', (0., 0., rear_bead_z-.1), (0., 0., .1))
        _create_line_mesh(root, group, 'Face X Axis', (-edge_radius, 0., 0.), (edge_radius, 0., 0.))
        _create_line_mesh(root, group, 'Face Y Axis', (0., -edge_radius, 0.), (0., edge_radius, 0.))
        if s.create_lug_guides:
            pcd_radius = s.pcd_mm / 2000.
            lug_radius = s.lug_diameter_mm / 2000.
            _create_lug_guides(root, group, s.lug_count, pcd_radius, lug_radius, 0., segments=s.lug_circle_vertices)
        if s.create_hub_guide:
            _update_hub_guide(root, group, s)
        s.rig_root = root
        extra = f'; {s.lug_count} lug circles in one mesh' if s.create_lug_guides else ''
        extra += '; ET hub guide' if s.create_hub_guide else ''
        self.report({'INFO'}, f'Created rim construction rig with mesh guides (meters; 1 Blender unit = 1 m){extra}')
        return {'FINISHED'}


class RIMPM_OT_Solve(bpy.types.Operator):
    bl_idname = 'rim_pm.solve'
    bl_label = 'Estimate Rim Camera'
    bl_description = 'Estimate plausible camera poses from a selected ring edge and fixed lens; result is not unique'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene, s = context.scene, context.scene.rim_pm
        if not s.image or not len(s.candidates):
            self.report({'ERROR'}, 'Load photo, select area, detect edge, choose candidate')
            return {'CANCELLED'}
        if not s.rig_root or s.rig_root.name not in scene.objects:
            self.report({'ERROR'}, 'Create the dimensioned rim rig first')
            return {'CANCELLED'}
        cam = _get_camera(scene, s)
        if cam.constraints:
            self.report({'ERROR'}, 'Remove camera constraints to solve')
            return {'CANCELLED'}
        try:
            if any(abs(float(v)-1.) > 1e-5 for v in s.rig_root.scale):
                raise rim_core.RimSolveError('Apply scale to the rim rig root before solving')
            dims = _image_dims(s)
            scene.render.resolution_x, scene.render.resolution_y = dims
            scene.render.resolution_percentage = 100
            scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.
            _set_background(scene, s)
            fx, fy, cx, cy = _frame_intrinsics(scene, cam, dims)
            ellipse = tuple(s.candidates[s.candidate_index].coords)
            answers = rim_core.solve_circle_camera_candidates(
                ellipse, _effective_edge_diameter(s)[0], fx, fy, cx, cy)
            s.solutions.clear()
            for answer in answers:
                item = s.solutions.add()
                item.center = answer['center'].tolist()
                item.rotation = answer['blender_rotation'].reshape(-1).tolist()
                item.rms = answer['error_px']
                item.angle = answer['inclination_deg']
            s.solution_index = 0
            _apply_solution(scene, s)
            if context.screen:
                for area in context.screen.areas:
                    if area.type == 'VIEW_3D':
                        area.spaces.active.region_3d.view_perspective = 'CAMERA'
            _redraw(context)
            self.report({'INFO'}, f'Estimated {len(answers)} possible poses; fit {answers[0]["error_px"]:.2f}px; check visually')
            return {'FINISHED'}
        except (rim_core.RimSolveError, ValueError, OverflowError, np.linalg.LinAlgError) as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


def _apply_solution(scene, s):
    sol = s.solutions[s.solution_index]
    M = Matrix(np.asarray(sol.rotation).reshape(3,3).tolist()).to_4x4()
    T = Matrix.Translation(Vector(sol.center))
    s.camera.matrix_world = s.rig_root.matrix_world @ T @ M
    scene.camera = s.camera


class RIMPM_OT_SwitchSolution(bpy.types.Operator):
    bl_idname = 'rim_pm.switch_solution'
    bl_label = 'Try Alternative Camera Pose'
    bl_description = 'Switch between the two pose solutions that may fit a single image ellipse'
    bl_options = {'REGISTER', 'UNDO'}
    offset: IntProperty(default=1)

    def execute(self, context):
        s = context.scene.rim_pm
        if not len(s.solutions):
            return {'CANCELLED'}
        s.solution_index = (s.solution_index+self.offset) % len(s.solutions)
        _apply_solution(context.scene, s)
        _redraw(context)
        return {'FINISHED'}


class RIMPM_OT_ViewCamera(bpy.types.Operator):
    bl_idname = 'rim_pm.view_camera'
    bl_label = 'View Rim Camera'
    bl_description = 'Activate the rim camera and image; do not change existing car match data'
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        s = context.scene.rim_pm
        if not s.camera or not s.image:
            self.report({'ERROR'}, 'Load a Rim Photograph first')
            return {'CANCELLED'}
        scene = context.scene
        scene.camera = s.camera
        w, h = s.image.size
        scene.render.resolution_x, scene.render.resolution_y = int(w), int(h)
        scene.render.resolution_percentage = 100
        if context.screen:
            for area in context.screen.areas:
                if area.type == 'VIEW_3D':
                    area.spaces.active.region_3d.view_perspective = 'CAMERA'
                elif area.type == 'IMAGE_EDITOR':
                    area.spaces.active.image = s.image
        _redraw(context)
        return {'FINISHED'}


def _draw_image():
    ctx = bpy.context
    area, region, scene = getattr(ctx, 'area', None), getattr(ctx, 'region', None), getattr(ctx, 'scene', None)
    if not area or area.type != 'IMAGE_EDITOR' or not region or not scene:
        return
    s = scene.rim_pm
    dims = _image_dims(s)
    if not dims or area.spaces.active.image != s.image:
        return
    w, h = dims
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')

    def draw_poly(points, color):
        points = [region.view2d.view_to_region(float(x)/w, 1.-float(y)/h, clip=False) for x,y in points]
        if not points:
            return
        pairs = []
        for start, end in zip(points, points[1:]+points[:1]):
            pairs.extend((start, end))
        batch = batch_for_shader(shader, 'LINES', {'pos': pairs})
        gpu.state.blend_set('ALPHA')
        shader.bind()
        shader.uniform_float('color', color)
        batch.draw(shader)
        gpu.state.blend_set('NONE')

    if s.roi_valid and s.show_roi:
        x0, y0, x1, y1 = s.roi_uv
        draw_poly([(x0*w,(1.-y0)*h), (x1*w,(1.-y0)*h),
                   (x1*w,(1.-y1)*h), (x0*w,(1.-y1)*h)], (.9, .75, .2, .75))
    if s.show_candidates and len(s.candidates):
        for i, c in enumerate(s.candidates):
            if i != s.candidate_index:
                continue
            pts = rim_core.ellipse_points(c.coords, n=128)
            draw_poly(pts, (.25, 1., .45, 1.))
            x, y = region.view2d.view_to_region(c.coords[0]/w, 1.-c.coords[1]/h, clip=False)
            blf.position(0, x+10, y+7, 0)
            blf.size(0, 13)
            blf.color(0, .4, 1., .6, 1.)
            blf.draw(0, f'Candidate {i+1}/{len(s.candidates)}')


def _panel_ui(layout, context, image_editor=False):
    """Compact staged UI; all v0.4.8 operators and settings remain accessible.

    UILayout.panel() stores expansion state in the *editor region* instead of
    scene data. Thus Image Editor and 3D View can display different steps,
    without changing any project/camera/solver settings.
    """
    s = context.scene.rim_pm

    if s.image:
        layout.label(text=f'Photo: {s.image.name[:28]}', icon='IMAGE_DATA')
    else:
        layout.label(text='Load a photo to begin', icon='INFO')

    # v0.4.12 uses fresh IDs so all sections start closed in existing workspaces,
    # even when earlier panel state had been expanded in v0.4.11.
    header, body = layout.panel('rimpm_v0412_photo_and_edge', default_closed=True)
    header.label(text='1. Photo & Edge', icon='FILE_IMAGE')
    if body is not None:
        col = body.column(align=True)
        col.operator('rim_pm.load_photo', text='Load Rim Photograph', icon='FILE_IMAGE')
        if s.image:
            col.prop(s, 'image', text='Photo')
        if image_editor:
            # Keep the exact operator in the Image Editor, including its label.
            col.operator('rim_pm.pick_area', text='1. Draw Rim Area')
        else:
            col.label(text='Select rim area in Image Editor', icon='INFO')
        row = col.row(align=True)
        row.enabled = s.roi_valid and bool(s.image)
        row.operator('rim_pm.detect', text='2. Detect Rim Edges', icon='VIEWZOOM')
        if s.candidates:
            row = col.row(align=True)
            prev = row.operator('rim_pm.switch_candidate', text='', icon='TRIA_LEFT')
            prev.offset = -1
            row.label(text=f'Edge {s.candidate_index+1} / {len(s.candidates)}')
            nxt = row.operator('rim_pm.switch_candidate', text='', icon='TRIA_RIGHT')
            nxt.offset = 1
        if image_editor:
            col.operator('rim_pm.manual_points', text='Fallback: 8 Edge Clicks', icon='EYEDROPPER')

    # 2 - The geometrical parameters actually needed in a typical workflow.
    header, body = layout.panel('rimpm_v0412_rim_geometry', default_closed=True)
    header.label(text='2. Rim Geometry', icon='MESH_CIRCLE')
    if body is not None:
        body.prop(s, 'nominal_diameter_in', text='Rim Diameter')
        body.prop(s, 'width_in', text='Rim Width')
        ring_box = body.column(align=True)
        ring_box.prop(s, 'photo_ring_type', text='Detected Ring')
        if s.photo_ring_type == 'MANUAL':
            ring_box.label(text='Manual position in Advanced', icon='INFO')
        elif s.photo_ring_type in {'FRONT_LIP', 'REAR_LIP'}:
            ring_box.prop(s, 'lip_overhang_mm')
        elif s.photo_ring_type == 'HUB_FACE' and not s.create_hub_guide:
            ring_box.prop(s, 'offset_et_mm')
        elif s.photo_ring_type == 'CENTER_BORE' and not s.create_hub_guide:
            ring_box.prop(s, 'center_bore_mm')
            ring_box.prop(s, 'offset_et_mm')

        diameter, certainty = _effective_edge_diameter(s)
        ring_box.label(text=f'Photo edge: {diameter:.1f} mm')
        if certainty == 'APPROX_BEAD':
            ring_box.label(text='Estimated - not a measured lip', icon='INFO')
        elif certainty == 'ASSUMED_CENTER_BORE':
            ring_box.label(text='Assumed center bore diameter', icon='INFO')
        body.prop(s, 'circle_vertices', text='Rim Circle Vertices')
        if s.rig_root:
            body.label(text='Construction rig exists', icon='CHECKMARK')
            body.operator('rim_pm.update_ring_guides', text='Update Ring Guides', icon='FILE_REFRESH')
            if s.create_hub_guide:
                body.operator('rim_pm.update_hub_guide', text='Update Ring & ET Guides', icon='EMPTY_AXIS')

    # Optional guides have their own collapsible sections, including enabled
    # switches in the headers so users need not open the section to toggle it.
    header, body = layout.panel('rimpm_v0412_lug_guides', default_closed=True)
    header.prop(s, 'create_lug_guides', text='Lug / Bolt Pattern Guides')
    if body is not None:
        if s.create_lug_guides:
            body.prop(s, 'lug_count', text='Lug Count')
            body.prop(s, 'pcd_mm', text='PCD (mm)')
            body.prop(s, 'lug_diameter_mm', text='Hole Diameter (mm)')
            body.prop(s, 'lug_circle_vertices', text='Lug Vertices', slider=True)
            body.label(text='All holes in one mesh object')
        else:
            body.label(text='Enable to create bolt-pattern guides')

    header, body = layout.panel('rimpm_v0412_hub_et', default_closed=True)
    header.prop(s, 'create_hub_guide', text='ET / Hub Guide')
    if body is not None:
        if s.create_hub_guide:
            body.prop(s, 'offset_et_mm', text='Offset ET (mm)')
            body.prop(s, 'center_bore_mm', text='Center Bore (mm)')
            body.label(text=f'Mounting plane Z: {_hub_guide_z(s)*1000:+.1f} mm')
            if s.photo_ring_type in {'FRONT_LIP', 'REAR_LIP', 'MANUAL'}:
                body.label(text='Verify lip/manual distance', icon='INFO')
        else:
            body.label(text='Enable to create center-bore guide')

    # Create the rig only after the photo, geometry and optional guides have
    # been configured. Keep this primary action visible when panels are folded.
    action = layout.row(align=True)
    action.enabled = not bool(s.rig_root)
    action.operator('rim_pm.create_rig', text='Create Modeling Rig', icon='MESH_CIRCLE')

    # 3 - Solve remains unchanged, including alternative pose and camera view.
    header, body = layout.panel('rimpm_v0412_camera', default_closed=True)
    header.label(text='3. Camera', icon='CAMERA_DATA')
    if body is not None:
        body.prop(s, 'lens_mm', text='Focal Length (mm)')
        row = body.row(align=True)
        row.enabled = bool(s.image and s.candidates and s.rig_root)
        row.operator('rim_pm.solve', text='Estimate Rim Camera', icon='TRACKING')
        if s.solutions:
            solution = s.solutions[s.solution_index]
            body.label(text=f'Contour error: {solution.rms:.2f} px')
            body.label(text=f'Inclination: {solution.angle:.1f} deg')
            body.operator('rim_pm.switch_solution', text='Try Other Pose', icon='FILE_REFRESH')
        row = body.row(align=True)
        row.enabled = bool(s.camera and s.image)
        row.operator('rim_pm.view_camera', text='View Rim Camera', icon='VIEW_CAMERA')
        body.label(text='One ring does not uniquely fix the camera', icon='INFO')

    # Rare settings and troubleshooting are intentionally out of the main flow.
    header, body = layout.panel('rimpm_v0412_advanced', default_closed=True)
    header.label(text='Advanced & Display', icon='PREFERENCES')
    if body is not None:
        body.prop(s, 'show_candidates', text='Show Edge Overlay')
        body.prop(s, 'show_roi', text='Show Selected Area')
        if s.candidates:
            body.label(text=f'Edge score: {s.candidates[s.candidate_index].score:.2f}')
        body.prop(s, 'fill_guide_faces')
        body.operator('rim_pm.repair_guide_wire',
                      text='Fix Old Rig Wire Overlays')
        body.prop(s, 'override_edge_diameter', text='Use Exact Diameter')
        if s.override_edge_diameter:
            body.prop(s, 'edge_diameter_mm')
        if s.photo_ring_type == 'MANUAL':
            body.prop(s, 'front_bead_seat_z_mm')
        body.label(text=f'Front bead Z: {_front_bead_z_mm(s):+.2f} mm')
        body.label(text='Selected photo ring is Z=0')
        if s.rig_root:
            body.prop(s, 'rig_root', text='Rig Object')
            body.label(text='Rebuild rig for lug topology changes')
        if s.camera:
            body.prop(s, 'camera', text='Rim Camera')


class RIMPM_PT_View(bpy.types.Panel):
    bl_idname = 'RIMPM_PT_view'
    bl_label = 'Rim PhotoMatch (Experimental)'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        _panel_ui(self.layout, context)


class RIMPM_PT_Image(bpy.types.Panel):
    bl_idname = 'RIMPM_PT_image'
    bl_label = 'Rim PhotoMatch (Experimental)'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'PhotoMatch'
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        _panel_ui(self.layout, context, image_editor=True)


CLASSES = (
    RIMPM_Ellipse, RIMPM_CameraSolution, RIMPM_Settings,
    RIMPM_OT_LoadPhoto, RIMPM_OT_PickArea, RIMPM_OT_Detect, RIMPM_OT_ManualPoints,
    RIMPM_OT_SwitchCandidate, RIMPM_OT_CreateRig, RIMPM_OT_UpdateHubGuide, RIMPM_OT_UpdateRingGuides, RIMPM_OT_Solve,
    RIMPM_OT_SwitchSolution, RIMPM_OT_ViewCamera, RIMPM_OT_RepairGuideWire,
    RIMPM_PT_View, RIMPM_PT_Image,
)


def register():
    global _RIM_DRAW_HANDLE
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.rim_pm = bpy.props.PointerProperty(type=RIMPM_Settings)
    # No bpy.data.scenes access during extension registration (_RestrictData).
    if not bpy.app.background:
        _RIM_DRAW_HANDLE = bpy.types.SpaceImageEditor.draw_handler_add(_draw_image, (), 'WINDOW', 'POST_PIXEL')


def unregister():
    global _RIM_DRAW_HANDLE
    if _RIM_DRAW_HANDLE is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_RIM_DRAW_HANDLE, 'WINDOW')
        _RIM_DRAW_HANDLE = None
    del bpy.types.Scene.rim_pm
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
