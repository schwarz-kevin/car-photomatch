# Multiple photomatches in one Blender scene

**No new Blender scene is required.** Every solved match is kept as a separate **camera object** in the same scene; the car model stays put.

## Create the next match

1. Finish the current match; consider renaming the camera in the Outliner (`Front 3-4`, `Rear 3-4`, etc.).
2. Optionally use **Pack Photo into .blend** to embed the active photograph.
3. Enable or disable **Reuse 3D Landmarks on New Match**:
   - **On** (default): keep the current pairs' names, enabled state, weights and 3D positions; clear all photo coordinates so you can click them in the new photo.
   - **Off**: delete the active landmark pairs and start with an empty list.
4. Click **New Photomatch**. The add-on creates a separate camera and independent camera datablock. It uses the previous camera's pose/lens as a starting point but **does not modify the old camera**.
5. Click **Load Reference Photo** and pick new photo coordinates. Solve the new match.
6. Repeat as many times as needed.

### Return to an earlier match

1. In **Reference & Camera**, select the older camera from the Camera field.
2. Click **View Selected Camera**. It makes that camera active, selects its attached photo and **restores its photo dimensions/aspect ratio** on the scene's render resolution.
3. Use **Global Match Display** and **Camera Fine Tune** to inspect/refine the camera manually.

**Important limitation:** Old *2D* landmark pairs are **not archived by camera**. The old camera's transform, focal length, and photo remain, so the match can be viewed and rendered, but to run the solver again for an older angle you must recreate its 2D pairs.

### Why aspect ratios can appear wrong

Blender's render resolution belongs to the **scene**, not to each camera. When you load a new photo, the scene resolution changes. Switching a camera using Blender's normal camera picker alone may keep the newer resolution. Prefer **View Selected Camera**, which resets the resolution from the old camera's photograph.

### What is global and what is per camera?

| Setting/data | Scope |
| --- | --- |
| Camera object, location, rotation, lens, shift | Each camera independently |
| Attached reference photograph | Each camera independently |
| Landmark pairs for current solve | Active scene state (older 2D points intentionally discarded) |
| Photo overlay opacity and front/behind layer | Shared across background images on all cameras in the **same scene** |
| Solid/Wireframe/X-Ray controls | Shared scene values, applied to **open 3D Viewports** showing that scene |
| Render resolution | One value per scene; restored by **View Selected Camera** |
| Car geometry | Shared (not copied or modified) |
