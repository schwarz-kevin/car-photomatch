# Settings reference — v0.4.12

## Car PhotoMatch

- **Load Reference Photo**: photo background and camera aspect.
- **Car Collection**: optional collection used for picking and model-scoped operations.
- **Add / Remove Landmark Pair**: pair a selected 3D point with a photographed 2D point.
- **Solve Camera**: numerical calibration of camera pose and optional focal length.
- **New Photomatch**: keeps the old camera/photo and creates a fresh camera, optionally reusing 3D landmarks.
- **View Selected Camera**: return to older camera/photo and restore aspect.
- **Camera Fine Tune**: manually edit camera transform, lens and shift.
- **Reference Photo Display**: enable photo, opacity and front/behind placement; **does not override Blender shading**.

## Rim PhotoMatch (Experimental)

All six sections start collapsed. In order:

1. **Photo & Edge**: load photograph, drag image selection, detect candidates, or fit 8 manually clicked points.
2. **Rim Geometry**: nominal diameter/width, detected physical ring type, rim circle vertex count, update guides.
3. **Lug / Bolt Pattern Guides**: optional lug count, PCD (mm), lug-hole diameter (mm), independent vertex count; all lug loops in one mesh object.
4. **ET / Hub Guide**: optional ET and center-bore measurement; mounting reference circle.
5. **Create Modeling Rig** button: generate construction meshes at current 3D cursor; disabled if rig exists.
6. **Camera**: assumed focal length, solve approximate camera, try alternative pose, view camera.
7. **Advanced & Display**: diagnostic overlays, exact diameter override, manual ring Z reference, old guide wire overlay repair.

**Units:** the modeling rig is created with Blender units interpreted as meters. Rim/PCD/hub dimensions are entered in mm or nominal wheel inches as labeled. A single ring photograph cannot uniquely recover the camera's complete perspective.
