# Installation and upgrades

**Compatible target:** Blender 5.2; later versions have not been comprehensively tested.

1. Download `car_photomatch_0_4_12_ui_workflow.zip` from [GitHub Release v0.4.12](https://github.com/schwarz-kevin/car-photomatch/releases/tag/v0.4.12) under **Assets**.
2. In Blender, open **Edit → Preferences → Get Extensions → Install from Disk** and select the **extension ZIP**.
3. If replacing an older Car PhotoMatch version, disable or uninstall the old extension before installing the new ZIP, then **restart Blender**.
4. Open **N → PhotoMatch** in the 3D Viewport. The Rim PhotoMatch panel is also visible in the Image Editor.

The extension ID is still `car_photomatch` and the existing `.blend` cameras and scene data should remain in the project. Before upgrading from 0.3.1, **save a backup of your .blend**. Do not install the GitHub repository Source code archive as the Blender extension.

If Shading looks wrong, note that Blender controls the viewport mode. Rim PhotoMatch's old guide meshes may also have forced wire overlays; see [Viewport and Camera](VIEWPORT_AND_CAMERA.md).
