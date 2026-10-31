# Car PhotoMatch

**Match Blender cameras to car photos — or build wheel rims from a calibrated photograph.**

Car PhotoMatch is a free, offline Blender **5.2** extension for automotive photo matching. The original car workflow aligns an existing 3D vehicle with a photograph using corresponding 3D/2D landmarks. The **experimental Rim PhotoMatch mode** uses a detected circular edge to estimate a modeling camera and create dimensioned mesh guides for rim modeling.

**Latest version:** `v0.4.12` · **License:** GPL-3.0-or-later · **Status:** Car photomatching user-tested; rim matching is experimental. Blender 5.2 runtime testing across systems is incomplete.

**[Download v0.4.12](https://github.com/schwarz-kevin/car-photomatch/releases/tag/v0.4.12)** · [Documentation](docs/TUTORIAL.md) · [Report a bug](https://github.com/schwarz-kevin/car-photomatch/issues)

> **Install:** From the release's **Assets**, download `car_photomatch_0_4_12_ui_workflow.zip`. Do **not** install GitHub's automatically generated **Source code (zip)**. The add-on runs locally without separately installed Python packages.

## Features

### Car PhotoMatch (existing model)

- Manually pair recognizable points on your 3D car mesh and photo; solve camera pose and optionally focal length.
- Reprojection-error feedback and adjustable camera parameters for refinement.
- **New Photomatch:** multiple independent camera matches in one Blender scene; previous camera and photograph remain accessible.
- **Reference Photo Display:** set photo visibility, opacity and photo-in-front/behind for all match cameras in the scene.
- **Blender controls Solid, Wireframe, Material Preview, Rendered and X-Ray.** The add-on no longer changes viewport shading modes.

### Rim PhotoMatch (experimental)

- Select a rough rim image area, detect multiple circular-edge candidates, or use the **8-click** fallback.
- Choose the photographed physical ring (bead seat, lip, center bore, hub face, or manual) and enter known wheel dimensions.
- Estimate camera poses with an **assumed focal length**; inspect alternative pose where available. One circular edge is **not sufficient** for a unique camera calibration.
- Create **mesh-circle** rim construction guides with controllable vertex count.
- Optionally create **one mesh object** holding all bolt/lug circles using lug count, PCD, hole size and vertex count.
- Optional **ET / hub mounting guide** using rim width, ET and center-bore diameter; update existing ring/ET guides.
- Compact workflow UI: collapsed sections, with **Create Modeling Rig** after geometry/lug/ET configuration and before camera solving.
- Fix Old Rig Wire Overlays action for older generated rig objects.

## Install in Blender 5.2

1. Download [`car_photomatch_0_4_12_ui_workflow.zip`](https://github.com/schwarz-kevin/car-photomatch/releases/tag/v0.4.12) from the **Assets** section.
2. In Blender, go to **Edit → Preferences → Get Extensions → Install from Disk**.
3. Select the **installer ZIP**, enable Car PhotoMatch if needed, and restart Blender after upgrading.
4. In a 3D Viewport or Image Editor, press **N** and open the **PhotoMatch** tab.

A local copy of the installer also lives at [`releases/car_photomatch_0_4_12_ui_workflow.zip`](releases/car_photomatch_0_4_12_ui_workflow.zip).

## Quick start — existing car model

1. Open a `.blend` with your car mesh. Click **Load Reference Photo** in Car PhotoMatch.
2. Split the workspace between a **3D Viewport** and **Image Editor** showing the photograph.
3. Click **Add Landmark Pair**; choose a corresponding 3D mesh feature and 2D image point.
4. Add at least six good pairs (preferably 8–15 spread across the vehicle); click **Solve Camera**.
5. Adjust photo transparency/placement in **Reference Photo Display**. Choose viewport shading yourself in Blender.
6. Use **New Photomatch** to create a second camera without duplicating the car model.

See [Car photomatching tutorial](docs/TUTORIAL.md).

## Quick start — modeling a rim from a photograph

1. In the Image Editor, open **Rim PhotoMatch (Experimental) → 1. Photo & Edge**, then **Load Rim Photograph**.
2. Click **Draw Rim Area** to drag a loose rectangle around the rim; click **Detect Rim Edges**, or use **Fallback: 8 Edge Clicks**.
3. Choose the matching highlighted contour. Under **2. Rim Geometry**, enter nominal diameter and width, choose **Detected Ring**, and set circle vertices.
4. Optionally enable **Lug / Bolt Pattern Guides** (count, PCD, hole diameter, vertices) and **ET / Hub Guide** (ET, center bore).
5. Click **Create Modeling Rig** beneath the geometry sections; the generated guides are separate meshes.
6. Expand **3. Camera**, enter an assumed focal length, and click **Estimate Rim Camera**. Inspect the result and use **Try Other Pose** if necessary.

See the [Rim PhotoMatch tutorial](docs/RIM_PHOTOMATCH.md) for the ring-reference and measurement limitations.

## Documentation

| Guide | Contents |
| --- | --- |
| [Installation](docs/INSTALLATION.md) | Install, upgrade and verify |
| [Car matching tutorial](docs/TUTORIAL.md) | Correspondences, solve and refine |
| [Rim matching tutorial](docs/RIM_PHOTOMATCH.md) | Edge detection, mesh guides, PCD and ET |
| [Multiple car photomatches](docs/MULTIPLE_PHOTOMATCHES.md) | Create, reuse landmarks and revisit cameras |
| [Reference photo display](docs/VIEWPORT_AND_CAMERA.md) | Transparency and front/behind; Blender shading |
| [Settings reference](docs/REFERENCE.md) | Controls and limitations |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Frequent problems and recovery |
| [Development and tests](docs/DEVELOPMENT.md) | Source structure and testing |
| [Publish next release](docs/PUBLISHING.md) | Git commands and release assets |
| [Changelog](CHANGELOG.md) | Version history |

## Limitations

- The experimental rim detector can select the wrong physical ring; verify the green contour.
- A **single circular edge** cannot uniquely solve focal length and camera pose. You must choose/assume a focal length and assess the result.
- Nominal rim diameter refers to bead-seat diameter, **not necessarily the visible outer lip**. Lip dimensions may be approximations; override using a known physical measurement for accuracy.
- Rim width alone does not determine spoke dish depth or the axial position of every photographed ring.
- Some rig topology changes require removing the old construction rig and creating another.
- For camera-photo overlays, Blender controls viewport shading; Car PhotoMatch controls only photo opacity and front/behind placement.

## Development

The repository includes Blender Python extension source, NumPy-based solver code, mocked/numerical tests, and a GitHub Actions workflow. The automated tests **do not replace** real Blender 5.2 UI testing.

Contributions and bug reports are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Distributed under **GPL-3.0-or-later**. See [LICENSE](LICENSE). No third-party photo or 3D-model assets are included.

## Transparency notice

Car PhotoMatch was developed primarily with AI-assisted coding to solve a specific problem in my automotive 3D workflow. I have tested the original photomatching workflow in my own projects and found it useful; the rim mode remains experimental. I'm sharing it openly so others can use it, test it, and contribute improvements. Bug reports and contributions are welcome.
