# Global photo overlay and camera fine-tuning

The v0.3.1 display settings are **scene-wide**. This includes cameras made with v0.2 and cameras with renamed objects, provided they have a camera background photo. Camera transform, focal length and actual photo selection are not modified by these global display controls.

## Make the photo visible in Solid mode

1. Enter camera view (**Numpad 0**).
2. Open **PhotoMatch → Global Match Display** in the 3D Viewport sidebar.
3. Click **Match View**. This selects **Solid**, enables **X-Ray**, turns on **Show Photo** and sets photo layer to **Photo Over Model**.
4. Adjust **Photo Opacity** (photo strength) and **Model Opacity (X-Ray)** (mesh transparency) to taste.
5. Switch to another camera through **View Selected Camera**. The same overlay settings continue to apply.

## Controls

| Control | Effect |
| --- | --- |
| **Match View** | Solid + X-Ray + photo over model |
| **Solid** | Solid, X-Ray off; image stays available |
| **Wire** | Wireframe; image remains available |
| **X-Ray** | Toggle the current X-Ray setting |
| **Show Photo** | Show/hide camera background photographs |
| **Photo Opacity** | Set alpha on every camera background photo in the scene |
| **Layer** | **Photo Over Model** (front) vs **Photo Behind Model** (back) |
| **Shading** | Shared setting for Solid or Wireframe in available viewports |
| **Use X-Ray** | Enable/disable semi-transparent model rendering in Solid |
| **Model Opacity (X-Ray)** | Blender X-Ray mesh alpha when enabled |
| **Model In Front** | Optional model visibility mode for mesh objects in the selected **Car Collection**; may obscure the photo |
| **Apply to All Cameras** | Reapply shared photo display to all cameras and current viewports |

**Blender behavior:** Camera background settings live on camera data; viewport Solid/Wire/X-Ray shading lives on **3D Viewport areas**. The plugin applies the shared scene state to open viewports displaying the same scene. If you switch to a different workspace whose viewport was not active, use **Apply to All Cameras** there.

## Camera Fine Tune

Open **PhotoMatch → Camera Fine Tune** (nested under the main 3D View panel). Select an old or new camera and click **View Selected Camera** before editing. Adjust:

- **Position / Rotation** — precise manual changes to the active camera.
- **Focal Length** — changes field of view and perspective compression.
- **Shift X / Shift Y** — changes framing without rotating the camera.

Fine-tuning changes the camera itself. The car model is untouched. The displayed solve RMS is from the last numerical solve and **is not automatically recomputed** for each manual camera edit.

### Recommended adjustment order

1. Confirm the image aspect ratio via **View Selected Camera**.
2. Set photo and model opacities to make both visible.
3. Adjust camera **rotation** to line up vehicle axes and front/rear perspectives.
4. Adjust **position** to align wheel and body features.
5. Adjust **focal length** if perspective compression is visibly wrong, and **shift** for small framing offsets.

If you still have the active matching points, prefer correcting markers and re-solving instead of excessive manual tweaking.
