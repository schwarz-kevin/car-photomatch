# Tutorial: match an existing car model to a photograph

This tutorial is for the primary workflow: **you already have a 3D car** and need to match a camera to a real photo without moving or deforming the model.

## Step 1 — Prepare the car

Open the Blender file and save a backup. Ideally, your car model has believable proportions and is grouped in one collection. Position/orientation of the car is not critical to the method, but avoid moving it while picking points. Select the car's collection in **PhotoMatch → Car Collection** to limit mesh ray-picking to its objects and avoid clicking through unrelated geometry.

Pick features that exist clearly in both the model and photograph. Good candidates include headlight corners, grille intersections, wheel hubs/centers, mirror tips, windshield corners, and bumper edges. **Do not pick arbitrary points along a curved silhouette** unless their identity matches reliably between image and model.

> For a wheel *center* that is not part of the mesh surface, use **Object Origin** (if the wheel object's origin is centered) or position the **3D Cursor** and use **3D Cursor**. Clicking the wheel mesh with the pick tool selects a point on its visible surface, not its exact geometric center.

## Step 2 — Load the image

In a 3D Viewport, press **N** to open the sidebar, choose **PhotoMatch**, and click **Load Reference Photo**. Select a source image. This action creates/uses a perspective camera, attaches the image as a camera background, and sets scene render dimensions to the image dimensions with square pixels.

Press **Numpad 0** to look through the active camera. Set up a second area as **Image Editor**, in ordinary **View** mode, showing the loaded image. Press **N** in the Image Editor to expose its **PhotoMatch** panel.

## Step 3 — Make corresponding landmark pairs

1. Press **Add Landmark Pair** in either PhotoMatch panel, and give it a descriptive name (for example `front_left_headlight_outer`).
2. Ensure this pair is selected in the list.
3. In the **3D Viewport** PhotoMatch panel, click **Click Point on Car Mesh**, then left-click the precise mesh position. Alternatively assign **3D Cursor** or **Object Origin**.
4. In the **Image Editor** PhotoMatch panel, select the **same pair**, click **Click Corresponding Photo Point**, then left-click the matching location in the photo.
5. Continue until you have **at least 6 complete enabled pairs**. Aim for **8–15** and distribute them across the car's length, width and height, not just the visible side surface.

Naming pairs well makes it easier to spot mistakes. Each row shows whether its **3D** and **2D** halves are set. If a pair is uncertain, adjust its **Weight**, or toggle its enable checkbox to exclude it from solving without deleting it.

## Step 4 — Solve

With the reference image and a perspective camera selected, press **Solve Camera**. If focal length is unknown, leave **Lock Focal Length** off; otherwise enable it and enter the calibrated focal length on the camera first. The solver optimizes the camera and reports **RMS Reprojection Error** in pixels.

- **Good solve:** 3D model features land close to their photo counterparts and projected cyan markers align with the photo markers.
- **Weak solve:** projection error is high or the body alignment is visibly wrong. Check whether a landmark was placed on the *wrong* corner, the mesh geometry differs from the photographed car, or points cluster on one flat region.
- **Unstable solve:** distribute points more broadly and give the camera a sensible initial angle before retrying. A single photo does not determine arbitrary lens distortion or fix incorrect vehicle proportions.

## Step 5 — Refine the photo overlay and camera

In the 3D View sidebar, open **Reference Photo Display**. Turn on **Show Reference Photo**, adjust **Photo Opacity**, and choose whether the photo appears **in front of** or **behind** the model. These reference-photo settings apply to photomatch cameras in the current scene.

Choose **Solid**, **Wireframe**, **Material Preview**, **Rendered**, and **X-Ray** using Blender's own viewport controls. Car PhotoMatch no longer changes the viewport shading mode. If an older rim construction guide still forces visible edges, use **Rim PhotoMatch → Advanced & Display → Fix Old Rig Wire Overlays** or hide its collection.

In the Image Editor, the overlay legend is:

| Visual | Meaning |
| --- | --- |
| Yellow photo cross | Your manually placed 2D landmark |
| Orange photo cross | Active/selected 2D landmark |
| Cyan cross | Projection of its 3D landmark through the current camera |
| Red segment | Reprojection residual from observed to projected position |

If something is off, **re-pick the inaccurate pair and solve again**. A small RMS error is useful but not sufficient: check body contours and points from different areas.

For tiny visual tweaks, expand **Camera Fine Tune** and adjust location, rotation, focal length or shifts. These manual changes are not a re-solve and do not automatically update the previously displayed RMS.

## Step 6 — Save and use another photo

Press **Pack Photo into .blend** if you want the image embedded in the project. Save the `.blend` file. To add a second angle in the **same scene**, follow [Multiple Photomatches](MULTIPLE_PHOTOMATCHES.md). Your earlier camera and photograph stay unchanged when you use **New Photomatch**.

## Practical marker recommendations for cars

- Use landmarks that are physically the **same** point in image and model.
- Include points near the **front and rear**, and points at **different heights**.
- Spread points across **width/depth** when possible, not only along one side.
- Weight unambiguous hard features more heavily than vague reflections or edges.
- Avoid reflections, highlights, flexible elements, and features hidden behind other geometry.
- If the car has aftermarket parts or the photo is retouched, some regions may be irreconcilable by camera alignment alone.
