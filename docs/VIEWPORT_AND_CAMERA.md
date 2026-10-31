# Reference Photo Display and camera controls (v0.4.12)

The extension **does not control Blender viewport shading**. Use Blender's own controls for Solid, Wireframe, Material Preview, Rendered and X-Ray.

## Shared photo controls

Expand **Reference Photo Display** in the 3D Viewport or Image Editor PhotoMatch tab:

- **Show Reference Photo**: enable/disable photo background display on match cameras.
- **Photo Opacity**: how visible the image is.
- **Photo Layer / Photo Placement**: show the reference in front of or behind the model.
- **Apply Display to All Cameras**: synchronize the active scene's reference-camera backgrounds if needed.

These settings are **per scene** and work with older photomatch cameras, not only newly generated ones.

## Revisit older car matches

Select an older camera and click **View Selected Camera**. The add-on can restore that camera's photographic aspect ratio. Under **Camera Fine Tune**, you can edit pose, lens and shift. The solver is only rerun when requested.

## Visual wire edges on construction rigs

Some old rim guides had **Object Properties → Viewport Display → Wireframe** enabled, independent of Blender's global shading. In Rim PhotoMatch **Advanced & Display**, use **Fix Old Rig Wire Overlays** to disable those forced overlays for existing rim-guide meshes. Edge-only guide circles remain geometry without faces; their edges can still be visible when overlays are enabled.
