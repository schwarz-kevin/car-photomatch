# Changelog

All versions below reflect the project's existing release history.

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
