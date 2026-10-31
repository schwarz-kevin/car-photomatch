# Car PhotoMatch v0.4.12 — Compact Rim Workflow UI

This is an **experimental Blender 5.2** add-on update based on the working v0.4.11 Rim PhotoMatch build.

## Changes in v0.4.12

- **All six Rim PhotoMatch sub-sections start collapsed**, in both the 3D Viewport and Image Editor (also when upgrading from an older expanded layout).
- Existing order stays the same: **1. Photo & Edge → 2. Rim Geometry → Lug / Bolt Pattern Guides → ET / Hub Guide → 3. Camera → Advanced & Display**.
- **Create Modeling Rig** now sits **after ET / Hub Guide and directly before 3. Camera**. It is always visible even when sections are collapsed.
- Once a construction rig exists, the Create button is disabled to avoid creating duplicate geometry. Use **2. Rim Geometry → Update Ring Guides** for adjustments to an existing rig, or remove the existing construction collection before creating a new rig.
- The camera solver, model guides, lug/ET placement, original Car PhotoMatch workflow, photo display controls and the v0.4.11 wire-overlay repair are unchanged.

## Installation

In Blender 5.2: **Edit → Preferences → Get Extensions → Install from Disk** and choose `car_photomatch_0_4_12_ui_workflow.zip`. Restart Blender after upgrading. The extension replaces the older version (`car_photomatch` ID), not your saved Blender camera data.

## UI order

1. Expand **Photo & Edge** to load an image and detect/select a ring.
2. Expand **Rim Geometry** to set the rim diameter, width, ring reference and circle vertex count.
3. Optionally expand **Lug / Bolt Pattern Guides** and **ET / Hub Guide** to enable and configure extra construction guides.
4. Click **Create Modeling Rig** directly underneath those sections.
5. Expand **Camera** to estimate the camera and inspect the match.

**Testing:** Python and mocked tests are available in the source bundle; Blender 5.2 UI has not been run in this environment.
