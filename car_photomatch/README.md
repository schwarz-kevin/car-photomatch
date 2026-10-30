# Car PhotoMatch 0.3.1 (Blender 5.2)

A local, offline Blender extension to fit a perspective camera to a photograph of a car using **an existing 3D car model**.

## v0.3.1 registration fix

Fixes the Blender extension error `'_RestrictData' object has no attribute 'scenes'` seen when enabling v0.3.0. v0.3.1 does not access scene data at registration time. The **Apply to All Cameras** button, **Match View** preset, global display sliders and **View Selected Camera** all continue to synchronize old and new cameras in the active scene. Existing photomatch cameras, poses, lens settings and saved photos are not touched by installation.

If v0.3.0 failed to enable, restart Blender before enabling v0.3.1 to avoid partially registered classes from the failed attempt.

## Install

1. Open **Blender 5.2**.
2. Choose **Edit > Preferences > Get Extensions > dropdown > Install from Disk**. (In builds using a different Preferences layout, look under Add-ons / Extensions.)
3. Select `car_photomatch_0_3_1.zip` and enable **Car PhotoMatch** if prompted. Upgrade/replace the earlier extension rather than enabling two copies at once. Keep a backup of your .blend file before updating.
4. In the **3D View**, press **N** and open the **PhotoMatch** tab.

The extension needs no network access or third-party pip packages. It uses NumPy bundled with Blender.

## Quick start

1. Open the `.blend` containing your car model. Put the car parts into a collection (optional but helpful for picking).
2. In **PhotoMatch**, choose **Load Reference Photo**. This sets the scene's render width/height to the image aspect, creates or uses the scene's camera, and adds the image to that camera's background. The scene's render pixel aspect is set to 1:1.
3. **Split the Blender editor into two areas**. Keep one area as **3D Viewport**, and set the second to **Image Editor**, with its mode set to **View**. Choose the loaded photograph in the Image Editor's image selector if necessary. Press **N** in each editor to reveal its PhotoMatch sidebar. To see the photo in the 3D camera view, press **Numpad 0**.
4. Press **Add Landmark Pair** in either editor. With that pair selected in the 3D View panel, press **Click Point on Car Mesh**, then click the corresponding mesh feature. For a wheel's geometric center, use **3D Cursor** or **Object Origin** instead (requires placing the cursor or setting the wheel object's origin correctly beforehand).
5. In the Image Editor PhotoMatch panel, select the same pair and press **Click Corresponding Photo Point**. Click the corresponding pixel on the photo.
6. Repeat for **at least 6 point pairs**. Recommended: 8–15 reliable landmarks distributed over different lengths, widths, and heights of the car (e.g. headlight edge, wheel centers, windshield corners, mirror tip, rear corner). Avoid placing all pairs on a single side plane.
7. Press **Solve Camera**. The plugin estimates camera position/rotation and, unless **Lock Focal Length** is enabled, focal length. It does **not** move or deform your car.
8. Inspect the wireframe or solid model in camera view over the camera background. In the Image Editor, **yellow crosses** are your photo points, **cyan crosses** are model-projected points, and **red lines** are residual errors. Select a pair and repeat its photo or mesh pick to refine it.
9. Press **Pack Photo into .blend** for portable projects, then save the Blender file. Marker pairs, camera, and match settings are saved with the scene.


## Global Solid-mode overlays (added in v0.3.0)

**All display settings are stored ONCE per Blender scene, not per photomatch camera.** They apply to **all cameras in that scene containing a camera background image**, including previously created v0.2 cameras, even if you renamed them. Camera position, rotation, lens, and background-image identity are not changed by these display controls.

Open the **PhotoMatch** tab in the 3D View and expand **Global Match Display**:

- **Match View**: Solid shading, X-Ray enabled, photo in front of geometry (transparent photo overlay).
- **Solid**: Solid shading, X-Ray off, keeps current reference photo visible.
- **Wire**: Wireframe shading, with the photo still visible.
- **X-Ray**: Toggle Solid-mode X-Ray without changing the camera.
- **Show Photo**: Enable/disable the reference background images on all cameras in the scene.
- **Photo Opacity**: Global image opacity for every camera background in the scene.
- **Layer — Photo Over Model / Photo Behind Model**: With **Over Model**, the camera photo is drawn semi-transparently in front of solid car geometry. With **Behind Model**, the photo sits behind the model; use X-Ray to reveal it.
- **Shading, Use X-Ray, Model Opacity**: Global scene controls for 3D Viewport shading. *Model Opacity* controls the X-Ray mesh opacity when X-Ray is on.
- **Model In Front** (optional): Acts on objects in **Car Collection** across all cameras, not on a particular camera. If enabled it may obscure the photo; the original `show_in_front` values of the objects are restored when disabled. Leave off for standard overlay matching.
- **Apply to All Cameras**: Forces the current shared settings onto older cameras and the currently open 3D Viewports.

**Revisit an older match without a new scene:** Choose its camera in the **Reference & Camera** selector, then click **View Selected Camera**. This activates the older camera, displays its previously attached photo in Image Editors, and **restores the original photo's render resolution/aspect ratio**, even if your newer photomatches used differently sized photos. Its camera pose/lens and image remain unchanged. Switch back the same way.

The **Camera Fine Tune** subpanel in the 3D View lets you edit the active camera's **position, rotation, focal length, and lens shift** manually. This includes older match cameras. Such manual adjustments do not recover deleted landmark pairs or automatically recompute the previously reported solve error.

**Important distinction:** Camera photo settings are applied to all camera backgrounds in the scene. Blender stores Solid/Wireframe/X-Ray shading **per 3D Viewport**, so the add-on applies the shared scene values to the open viewports showing that scene when you use its controls. A viewport in a different workspace that was not open may need **Apply to All Cameras** when you switch to it. The camera itself still remembers its photo.

**Updating v0.2/v0.3.0:** Install v0.3.1 over it, reopen your .blend file, and choose **Match View**. Old camera background photos are detected and can be shown in front of Solid geometry. For an older camera with a different aspect ratio, use **View Selected Camera** rather than Blender's camera selector alone.

## Multiple photomatches in the SAME scene (new in v0.2.0)

You do **not** need multiple Blender scenes or a photo-match manager.

1. Finish and solve the first photograph. Check its overlay, and optionally **Pack Photo into .blend** before continuing.
2. In the **PhotoMatch** sidebar, choose **Reuse 3D Landmarks on New Match** (on by default):
   - **Enabled:** keep the 3D positions, mesh-object references, pair names and weights; clear each pair's 2D photo coordinates.
   - **Disabled:** remove all landmark pairs, including their 3D positions.
3. Click **New Photomatch**. The old camera stays in the **same scene**, in the Outliner, at its solved pose, with its reference photo still attached. A **new independent camera** is created and made active, initially using the previous camera's lens/pose as a starting estimate. The old camera is not moved or modified.
4. The active photo and current 2D landmarks are cleared. **Load Reference Photo** to import your next angle, click its corresponding photo points (or create entirely new pairs), then **Solve Camera**.
5. Repeat for other views. Every solved view remains available as its own Blender camera object. **The model geometry is never copied or modified.**

**Important:** Old 2D matching points are intentionally **not saved**, so you cannot re-solve an old view unless you manually create its point pairs again. This is intentional, based on the requested workflow.

**Also important — varying aspect ratios:** Blender has one render resolution per scene, not per camera. In v0.3, **View Selected Camera** automatically restores the original photo dimensions and square-pixel aspect for the camera you choose. Changing the active camera by another Blender command may require that button to restore the correct aspect ratio.

### If you have already installed v0.1.0

Your current camera and point pairs remain in your saved `.blend` scene. After updating the extension, clicking **New Photomatch** starts the next match without changing your existing solved camera. Save a backup `.blend` before upgrading, as with any add-on update.


## Controls

- **Reuse 3D Landmarks on New Match**: keep 3D points but erase their old 2D photo coordinates when making another camera.
- **New Photomatch**: preserve old camera/background, create an independent new camera in this scene, and reset current match.
- **Car Collection**: optional filter for mesh picking. Hide non-model objects that may intercept clicks.
- **Lock Focal Length**: fit camera pose only; recommended if lens calibration is known.
- **Outlier Threshold (px)**: Huber loss transition. Increase for rough initial landmark picks; reduce for precise refinement.
- **Weight**: downweight ambiguous landmarks and upweight precise ones.
- **Enabled**: exclude questionable pairs without deleting them.
- **Photo Opacity**: control all reference camera-background opacity throughout the scene (v0.3).
- **Show Landmark Overlays**: display point IDs in 3D and 2D editors.
- **Show Reprojection Errors**: display projected points and residual lines in the Image Editor.

## Current limitations

- **Blender 5.2 runtime testing has NOT been performed in this delivery environment**. Solver logic was tested as standalone NumPy; registration, modal picking and GPU overlay operations must be smoke-tested in Blender.
- Perspective/pinhole camera only. No fisheye/orthographic solve, distortion coefficients, rolling shutter, or automatic lens-shift estimation.
- Camera shift is retained (not optimized). Focal length is bounded to 8–300 mm. Camera constraints must be disabled before solving.
- The initial pose normally comes from an algebraic DLT estimate using spatially distributed landmarks. If the points are coplanar or the initializer fails, manually point the Blender camera approximately toward the car and solve again.
- A photo cannot uniquely determine correct camera and model dimensions if the mesh differs from the photographed vehicle. Favor known car geometry and accurate points.
- Mesh-hit locations are stored as positions **relative to the picked object**; they follow object transforms, but not subsequent mesh-topology or vertex deformation changes. Cursor-defined points are stored in world coordinates.
- The add-on does not automatically create a split-screen workspace or automatically detect wheel/headlight landmarks.
- The plugin adjusts render resolution, render pixel aspect, and camera background setup when you load a photo. These are intentional scene changes.
- Image-overlay positions use Blender's Image Editor normalized View2D coordinates. Ensure the editor is in regular Image **View** mode rather than UV Edit mode.

## Developer notes

`solver.py` is Blender-independent and uses NumPy alone. Its eight synthetic tests cover projection, DLT initialization, camera optimization, lens locking, image noise, outlier resistance, planar geometry, and error handling. Two additional Blender-free mocked tests exercise the new-match reset behavior. Four additional tests check global opacity/layer behavior, legacy cameras and viewport shading scoping; a registration regression test checks that enabling the extension does not access the restricted scene database. Run with Python:

```bash
python -m unittest discover -s car_photomatch_tests -v
```

Recommended Blender integration smoke test: install the extension in Blender 5.2, load a photo, make 6–10 3D/2D pairs on a known car model, solve it, click **New Photomatch** with reuse enabled, verify that the original camera still has its photo and unchanged pose, create and solve a second image, switch both via **View Selected Camera**, check **Photo Over Model** in Solid, change global opacity and verify both cameras, and repeat with reuse disabled. Then save and reopen the `.blend` and disable/re-enable the extension to check drawing-handler cleanup.

## File layout

```text
car_photomatch_0_3_1.zip
  blender_manifest.toml
  __init__.py
  solver.py
  README.md
```

License: GPL-3.0-or-later (see SPDX identifiers in the code and manifest).
