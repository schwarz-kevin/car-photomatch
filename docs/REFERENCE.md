# Feature and control reference

## Reference & Camera

- **Reuse 3D Landmarks on New Match** — choose whether New Photomatch keeps the active 3D point positions.
- **New Photomatch** — keep previous camera+photo; create a **new camera datablock**, clear active reference and current photo points, optionally keep 3D points.
- **Load Reference Photo** — load an image and attach it to selected/current camera; set scene render dimensions and square pixels.
- **Photo** — reference image for the **current** matching operation.
- **Camera** — camera object to be activated/used.
- **View Selected Camera** — activate camera, load its attached background photo into Image Editors, restore render dimensions.
- **Setup / Refresh Camera Overlay** — attach/update the active image as the camera's background.
- **Pack Photo into .blend** — pack the *current* reference image into the `.blend` file. Images associated with older cameras can be packed from Blender's Image Editor as needed.

## Landmark Pairs

- **Add / Remove Landmark Pair** — modify list of correspondences.
- **3D Car Mesh Pick** — raycast in 3D viewport; optional **Car Collection** filter restricts picking.
- **3D Cursor / Object Origin** — set the 3D point from cursor or origin rather than a surface click.
- **Photo Point Pick** — click matching 2D point in Image Editor in **View** mode.
- **Photo UV** — normalized image position, bottom-left origin; editable on a selected pair.
- **Weight** — relative confidence in the pair; range 0.05–20.
- **Enabled checkbox** — include or exclude a pair from the solve without deleting it.
- **Show Landmark Overlays** — show on-screen point indicators.
- **Show Reprojection Errors** — show model projections and residual lines in Image Editor.

## Solver

- **Solve Camera** — camera translation/rotation and optional lens optimization based on at least **6 complete enabled** pairs; leaves the car geometry untouched.
- **Lock Focal Length** — preserve existing lens and solve pose only; useful with known calibrated lenses.
- **Outlier Threshold (px)** — transition for robust loss. Larger allows more pixel error before downweighting; default 12 pixels.
- **Solver Iterations** — limit nonlinear optimization iterations; default 80 (adjustable 10–200).
- **RMS Reprojection Error** — pixel error displayed after a completed solve; should be judged together with visual alignment.

## Global Match Display

See [Solid view and camera controls](VIEWPORT_AND_CAMERA.md). Photo alpha/placement/visibility are applied to **all cameras with background photographs in the same scene**, while Solid/Wire/X-Ray states are applied to available viewports showing that scene.

## Technical method

The source module `car_photomatch/solver.py` contains NumPy-only camera calibration. It uses a DLT-based camera initializer when point geometry permits, followed by robust nonlinear minimization of reprojection residuals. The Blender integration module contains panels, drawing handlers, scene settings and point picking. It uses Blender's camera projection to check the final error.

## Limitations

- Perspective (pinhole) camera model only; no automatic lens-distortion estimation or fisheye/orthographic support.
- The solver optimizes camera pose and (optionally) focal length; **lens shift is not optimized** and must be entered manually.
- Focal length has internal limits of **8–300 mm** in solve mode.
- Need ≥6 reliable pairs; coplanar, clustered or nearly collinear features can be unstable. A decent starting pose helps when initialization fails.
- Camera constraints prevent solving and must be removed or disabled first.
- Surface landmarks are stored as **object-local locations** and follow object transformations, but not arbitrary mesh topology/deformation changes. Cursor-defined points are world-space.
- Camera/photo alignment depends on model accuracy, camera parameters and image authenticity. Cropping or perspective correction can undermine a pinhole fit.
- The add-on does not automatically create a two-pane workspace or recognize vehicle features.
- Existing camera positions and photos persist when making a new match, but previous 2D landmarks are **not archived for later re-solving**.
- The active photo is packable from the sidebar; older photos may need separate packing in Blender if you require a self-contained project.
