# Changelog

## [0.4.12] — 2026-10-31 (experimental)

- Compact Rim PhotoMatch UI: all workflow sections start collapsed.
- **Create Modeling Rig** moved after rim/bolt/ET settings and before camera solving; button disables if rig already exists.
- Preserves existing car matching, rim solver, photo display and wire-overlay correction.

## [0.4.11] — 2026-10-31 (experimental)

- Prevent new rim guides from forcing mesh wire overlays; add action to repair old rig wire overlays.

## [0.4.10] — 2026-10-31 (experimental)

- Remove add-on control of Blender viewport shading and X-Ray. Retain only reference-photo opacity and front/behind placement.

## [0.4.9] — 2026-10-31 (experimental)

- Introduce compact, collapsible rim UI sections.

## [0.4.8] — 2026-10-31 (experimental)

- Calculate photographed ring diameter from selected reference type when possible; retain optional exact override.

## [0.4.7] — 2026-10-31 (experimental)

- Allow photographed ring reference selection (bead seat, outer lip, hub face and manual modes) for axial alignment.

## [0.4.6] — 2026-10-31 (experimental)

- Add ET / center-bore mounting guide and update action.

## [0.4.5] — 2026-10-31 (experimental)

- Generate lug-hole circle guides as one mesh object with independent vertex control.

## [0.4.2–0.4.4] — 2026-10-31 (experimental)

- Mesh ring guides, lug pattern controls, and display fixes.

## [0.4.0–0.4.1] — 2026-10-30 (experimental)

- Introduce Rim PhotoMatch with approximate ellipse detection, camera pose candidates and construction guides.
- Fix missing rim-selection UI control.

## [0.3.1] — 2026-10-30

### Fixed

- Avoid accessing `bpy.data.scenes` in add-on registration, resolving `'_RestrictData' object has no attribute 'scenes'` during extension enablement.
- Preserve global display behavior and earlier photo cameras.

## [0.3.0] — 2026-10-30

### Added

- Global Solid-mode matching display: photo layering/opacity, Solid/Wireframe presets and X-Ray controls across cameras in a scene.
- View Selected Camera action to restore older photos and render aspect ratios.
- Camera Fine Tune controls for position, rotation, focal length and lens shift.

## [0.2.0] — 2026-10-30

### Added

- New Photomatch creates an independent camera in the same scene while keeping the previous camera and its photo.
- Option to reuse current 3D landmarks without keeping old photo point coordinates.

## [0.1.0] — 2026-10-30

### Added

- Manual 3D/2D landmark matching and camera solving.
- Reference image loading, camera overlay, reprojection error display and photo packing.
