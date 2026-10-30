# Development and test guide

## Source structure

```text
car_photomatch/
  blender_manifest.toml   Blender 5.2 extension metadata and permissions
  __init__.py             Blender panels, operators, properties, viewport overlays
  solver.py               Blender-independent NumPy camera solver
  README.md               Original extension usage notes
car_photomatch_tests/
  test_solver.py           8 numeric solver tests
  test_new_match.py        2 new-camera reset tests using stubs
  test_global_display.py  4 global display tests using stubs
  test_registration.py    1 registration regression test
```

The source folder is deliberately retained in its working v0.3.1 state. The prebuilt release ZIP in `releases/` comes from that version, rather than from a modified or unverified rebuild.

## Run automated tests outside Blender

Install a normal Python 3 environment with NumPy, then run from the repository root:

```bash
python -m pip install numpy
python -m unittest discover -s car_photomatch_tests -v
```

15 tests cover solver projection/initialization/optimization, landmark resets, global photo controls, viewport scoping and restricted-registration safety. The Blender-facing functions are tested with stubs / AST extraction; those tests **do not** simulate the real viewport drawing engine or prove Blender compatibility.

## Build and validate with Blender 5.2

Blender's extension command-line tools can validate and build an extension from a directory containing `blender_manifest.toml`:

```bash
blender --command extension validate releases/car_photomatch_0_3_1.zip
blender --command extension build --source-dir car_photomatch --output-dir dist
```

If your Blender build uses different validation arguments, run `blender --command extension validate --help`. You can also validate a manifest from within the extension source folder (`cd car_photomatch` first):

```bash
blender --command extension validate
```

See official [Blender extension documentation](https://docs.blender.org/manual/en/5.2/advanced/extensions/getting_started.html) for current syntax. The `releases/` artifact already contains the original extension ZIP with its manifest at archive root.

## Recommended manual smoke test in Blender

1. Install the extension, enable it, verify the sidebar appears and no registration errors occur.
2. Load a car mesh and photograph, pick 8–12 corresponding points and solve.
3. Verify projected point/error overlays in Image Editor and photo visibility in Solid camera view.
4. Toggle Match View, Solid, Wire, X-Ray, Photo Opacity, Model Opacity and placement.
5. Create a new photomatch with **reuse on**, confirm the new camera is independent and old photo/lens/pose remain.
6. Create another match with **reuse off**, confirm points are cleared and old cameras remain.
7. Switch to both older cameras with **View Selected Camera**, verify photo/image dimensions and shared display behavior.
8. Fine-tune camera pose/lens, save/reopen the file and check persistence.
9. Disable/re-enable the add-on and watch the system console for draw-handler or registration exceptions.

## Contribution guidelines

Follow [CONTRIBUTING.md](../CONTRIBUTING.md). Prefer focused pull requests and regression tests. Code is GPL-3.0-or-later, and source files identify this with SPDX headers. Avoid committing copyrighted reference photos or proprietary car meshes.
