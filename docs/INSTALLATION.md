# Installation and upgrading

## Requirements

- Blender **5.2** (this release's minimum supported version).
- A car model in a `.blend` project and a local reference photograph (PNG/JPG etc.).
- No internet connection or extra Python packages are needed by the extension once installed. The solver uses Blender's bundled NumPy.

## Install for everyday use

1. Download **[`../releases/car_photomatch_0_3_1.zip`](../releases/car_photomatch_0_3_1.zip)** from this repository or from a GitHub Release.
2. Launch Blender and open **Edit → Preferences → Get Extensions**.
3. Open the menu at the top right and choose **Install from Disk** (Blender also accepts drag-and-drop of extension ZIP files in supported builds).
4. Pick `car_photomatch_0_3_1.zip` **without extracting it**.
5. Enable **Car PhotoMatch** if it is not already enabled.
6. Open a **3D Viewport** → press **N** → choose the **PhotoMatch** tab. The extension also adds a sidebar in **Image Editor**.

**Important:** do not attempt to install the *complete repository archive* as an extension: that archive includes documentation, tests and another ZIP. The actual installable package is `releases/car_photomatch_0_3_1.zip`, whose root contains `blender_manifest.toml`.

## Upgrade from v0.1, v0.2 or v0.3.0

1. **Back up your `.blend`** before changing add-on versions.
2. Disable/remove the previous version in Blender's extension preferences, as appropriate for your install. Avoid having duplicate add-on copies enabled.
3. If v0.3.0 previously showed `'_RestrictData' object has no attribute 'scenes'`, **restart Blender** to clear any partial registration state.
4. Install the v0.3.1 extension ZIP using the steps above.
5. Reopen your saved project. Previous solved camera objects and background photos are stored in the `.blend` file; you can select an old camera and click **View Selected Camera**.
6. Open **Global Match Display** and click **Apply to All Cameras** to synchronize saved older camera backgrounds with the shared display settings.

The add-on does not intentionally move or delete the old cameras when upgrading. Existing `.blend` data is distinct from the installed Python extension.

## Verify the install

- **PhotoMatch** appears in the 3D Viewport's **N sidebar**.
- You can find **Load Reference Photo**, **Add Landmark Pair**, **Solve Camera**, **New Photomatch** and **Global Match Display**.
- A small test photo can be loaded into the camera background.

## Troubleshooting installation

If the tab is missing, check whether the extension is enabled; close/reopen Blender if you replaced an earlier version. If Blender reports a Python error, open its console and include the **complete traceback**, Blender version, add-on version, and the action that caused the error in a bug report. See [Troubleshooting](TROUBLESHOOTING.md).
