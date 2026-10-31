# Development and testing

## Structure

- `car_photomatch/__init__.py`: main car landmark operators, UI and global reference-photo display.
- `car_photomatch/solver.py`: numerical camera optimizer.
- `car_photomatch/rim_mode.py`: experimental rim UI, image selection and rig operators.
- `car_photomatch/rim_core.py`: ellipse detection/fitting and circle camera solution candidates.
- `car_photomatch/rim_guides.py`: geometry and axial reference helpers.
- `car_photomatch/blender_manifest.toml`: Blender extension metadata.
- `car_photomatch_tests/`: Blender-free unit tests and mocked tests.
- `.github/workflows/tests.yml`: CI checks.

## Run tests outside Blender

Install Python 3.11+ and run:

```bash
python -m pip install numpy pytest
python -m pytest -q car_photomatch_tests
```

Unit tests do not emulate all Blender context, GPU drawing or Blender's editor UI behavior. Always run end-to-end Blender 5.2 tests for released builds, especially panel registration, Image Editor picking, background photos, overlays and saved project reload.

## Package extension ZIP

Zip **the contents** of `car_photomatch/` so `blender_manifest.toml` is at the root of the archive. Do not zip the whole repository to install into Blender. Check the `id`, version and license metadata.
