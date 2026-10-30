# Troubleshooting and FAQ

## I installed the GitHub ZIP but Blender rejects it

There are **two ZIP types**: the **GitHub repository ZIP** (source/docs/tests) and the **Blender extension ZIP** (`releases/car_photomatch_0_3_1.zip`). Install the **latter** using **Get Extensions → Install from Disk**. Its archive root must contain `blender_manifest.toml`.

## `'_RestrictData' object has no attribute 'scenes'`

This was the v0.3.0 registration bug. Install **v0.3.1**, remove/disable the broken v0.3.0 install, and **restart Blender** before re-enabling. v0.3.1 avoids reading `bpy.data.scenes` during registration.

## No PhotoMatch tab appears

Check **Preferences → Get Extensions** to confirm the add-on is enabled. In **3D Viewport** or **Image Editor**, press **N** and choose **PhotoMatch** in the sidebar. Restart Blender if you recently changed versions.

## I cannot see the photo in Solid mode

1. Ensure you're looking through the correct camera (**Numpad 0**).
2. Choose the camera in **Reference & Camera** and click **View Selected Camera**.
3. Open **Global Match Display**, click **Match View** and enable **Show Photo**.
4. Try **Photo Over Model** and increase **Photo Opacity**.
5. Check your camera has a background image; load/reapply it if needed.
6. If a new workspace is showing stale shading settings, click **Apply to All Cameras**.

## I switched to an older camera and the image is stretched/cropped

Blender uses one render resolution per scene. Switch with **View Selected Camera**, not only Blender's general camera picker; it restores the photo's width/height ratio.

## Photo markers or clicks are in the wrong place

Use the Image Editor in its ordinary **View** mode, not UV editing. Show the same image selected as the active reference. Zoom enough to click a visible feature precisely. Ensure you're selecting the same pair row in the 3D View and Image Editor.

## Solver says it needs at least six pairs

You need at least **six enabled pairs** containing **both 3D and 2D** positions. Click a mesh point *and* a matching photo point for each pair; check whether any pair is disabled.

## Camera solve fails or looks wrong

- Check for mismatched photo/model features and badly placed points.
- Place points in different regions of the vehicle, including distinct depths and heights.
- For a wheel center, use the wheel object's origin (if correct) or the 3D Cursor. A click on the tire surface is a different 3D location.
- Disable/downweight ambiguous points, then retry.
- Lock lens if the photo's calibrated focal length is known; otherwise let the solver estimate it.
- Give the camera a rough sensible starting pose if a geometry-based initial estimate fails.
- Disable/remove camera constraints.
- Account for wide-angle lens distortion or a photo with strong perspective edits; these are not corrected by the plugin.

## I lost the previous match's point markers after New Photomatch

This is intentional. v0.3.1 preserves **old camera pose/lens/photo**, not its old 2D matching points. You can revisit the old camera and manually fine-tune it, but to **re-solve** with markers you must recreate the photo points.

## Do global settings change every camera in my entire .blend file?

No. They apply to cameras with background photos **inside the active scene**. They are not global across unrelated Blender scenes. Viewport shading is an area setting, and the add-on updates open viewports showing that scene.

## My photos disappeared after moving the `.blend` to another computer

A camera background can refer to an external image file. Pack relevant images into the Blender project before sharing it. **Pack Photo into .blend** packs the active image; use Blender's Image Editor packing tools for older-camera reference images as needed.

## How to file a useful bug report

Include your Blender version, Car PhotoMatch version, your operating system, what you clicked, the **full Python traceback**, and whether the issue reproduces on a simple scene. Attach example images/models only if you have permission to share them. See [Contributing](../CONTRIBUTING.md).
