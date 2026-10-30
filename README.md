# Car PhotoMatch

**Match Blender cameras to car photos using an existing 3D model.** Car PhotoMatch is a free, offline Blender **5.2+** extension built for automotive photomatching. Pick corresponding 3D car features and 2D photo points, solve the camera, and compare the result over the photograph in Solid view.

**Release:** `v0.3.1` · **License:** GPL-3.0-or-later · **Status:** user-tested photomatching workflow; automated tests pass. Blender API behavior may vary across builds.

> **Installing?** Download **[`car_photomatch_0_3_1.zip`](releases/car_photomatch_0_3_1.zip)**. Install **that ZIP**, not the complete GitHub repository ZIP. No separate Python packages or network access are required inside Blender.

## Highlights

- **Model-first camera solve:** calibrate camera position, orientation and optionally focal length to an existing 3D vehicle.
- **Manual landmarks:** match a clicked 3D mesh location (or cursor/object origin) with a corresponding photo pixel.
- **Multiple photographs, one Blender scene:** **New Photomatch** keeps the old solved camera and photo, creates a separate camera, and optionally reuses 3D landmarks. No duplicated car geometry.
- **Global Solid-mode match view:** photo overlay opacity, photo-over-model/behind-model, Solid/Wireframe, X-Ray and X-Ray model opacity are shared by all match cameras **within the same scene**.
- **Revisit older cameras:** **View Selected Camera** restores the selected camera's photo and its aspect ratio; **Camera Fine Tune** edits camera pose, lens and shifts.
- **Visual feedback:** marker IDs, photo/model projection crosses, error vectors and RMS error after solving.
- **Local and offline:** Python, Blender API and bundled NumPy only.

## Install in Blender

1. Download [`releases/car_photomatch_0_3_1.zip`](releases/car_photomatch_0_3_1.zip).
2. Open **Blender 5.2** → **Edit → Preferences → Get Extensions** → top-right drop-down → **Install from Disk**.
3. Select the downloaded **extension ZIP**, and enable **Car PhotoMatch** if needed.
4. In the **3D Viewport**, press **N** and select the **PhotoMatch** tab.

If upgrading from v0.3.0, restart Blender before enabling v0.3.1. See [installation and upgrades](docs/INSTALLATION.md).

## 5-minute matching tutorial

1. Open your `.blend` with an existing car model. Optionally select its collection under **Car Collection**.
2. Click **Load Reference Photo** in the **PhotoMatch** sidebar; enter camera view with **Numpad 0**.
3. Split your workspace into a **3D Viewport** and an **Image Editor** in ordinary **View** mode, showing the same photo. Both editors have a **PhotoMatch** sidebar.
4. Click **Add Landmark Pair**. In 3D View, choose **Click Point on Car Mesh** and click a distinctive feature. In Image Editor, choose **Click Corresponding Photo Point** and click that feature in the photograph.
5. Repeat for **at least 6** complete pairs, preferably **8–15** spread across the car's length, width and height (wheel hubs, light corners, windshield corners, etc.).
6. Click **Solve Camera**. Inspect the photo/model overlay, and refine inaccurate landmarks if needed.
7. For a second photograph, select **Reuse 3D Landmarks on New Match** (optional), click **New Photomatch**, load the next photo and solve again. Your earlier camera remains intact.
8. Select any earlier camera, then click **View Selected Camera** to return to that match. For a Solid-mode blend, open **Global Match Display** and choose **Match View**.

For point-picking tips, worked examples and fine-tuning, read the [step-by-step tutorial](docs/TUTORIAL.md).

## Documentation

| Guide | What it covers |
| --- | --- |
| [Installation and upgrading](docs/INSTALLATION.md) | Install, replace old versions, verify the add-on |
| [Photomatching tutorial](docs/TUTORIAL.md) | Prepare a car, pair markers, solve, refine, save |
| [Multiple camera matches](docs/MULTIPLE_PHOTOMATCHES.md) | New Photomatch, reuse markers, switch to old cameras |
| [Solid-mode overlays and camera adjustment](docs/VIEWPORT_AND_CAMERA.md) | Shared display controls, X-Ray, opacity, fine tune |
| [Control reference](docs/REFERENCE.md) | All panels, options, matching data and solver limitations |
| [Troubleshooting and FAQ](docs/TROUBLESHOOTING.md) | Installation, photo visibility, inaccurate matching |
| [Developing and testing](docs/DEVELOPMENT.md) | Code structure, tests, Blender integration checks |
| [Publishing to GitHub](docs/PUBLISHING.md) | Uploading source and creating a GitHub Release |
| [Changelog](CHANGELOG.md) | Version history |
| [Contributing](CONTRIBUTING.md) | Bug reports and contribution notes |

## How camera matching works

Each landmark pair contains a known 3D position on the car and its matching 2D image coordinate. A numerical optimizer minimizes weighted camera **reprojection error** using a robust loss. It can estimate camera orientation, translation and focal length, or hold focal length fixed. The car mesh itself is not modified. Poorly distributed or inaccurate points, incorrect model proportions, and lens distortion can limit accuracy.

## Project files

```text
car_photomatch/                Blender extension source (manifest, UI, solver)
car_photomatch_tests/          NumPy + mocked Blender-free automated tests
releases/car_photomatch_0_3_1.zip  Installable Blender extension
.github/workflows/            GitHub Actions test workflow
.github/ISSUE_TEMPLATE/       Bug/feature request forms
docs/                         Tutorials and detailed documentation
LICENSE                       GPL v3 license text (code: GPL-3.0-or-later)
```

The **release ZIP** has `blender_manifest.toml` at its archive root. The **GitHub repository ZIP** contains source, tests and documentation and is **not** the Blender installer.

## Compatibility and scope

- Designed for **Blender 5.2** and perspective cameras. Earlier versions are not supported; later versions are not guaranteed.
- No automatic wheel identification, silhouette solve, lens-distortion correction or saved 2D points for *past* match cameras.
- All match cameras share the same scene's render resolution; **View Selected Camera** restores the selected photo dimensions. Global match display settings are **per scene**, while viewport shading is applied to open viewports showing that scene.
- Automated tests cover solver logic and mock-based add-on behavior. Blender integration tests should be completed on the target machine; see [development notes](docs/DEVELOPMENT.md).

## License

Car PhotoMatch is distributed under **GPL-3.0-or-later**. See [LICENSE](LICENSE). The code's SPDX tags and `blender_manifest.toml` identify the license. Reference photographs and 3D models are not included; you are responsible for your own rights to those assets.

## Transparency Notice

Most of this code was **vibe coded** but it solves a niche use case. I hope some people might participate from this.
