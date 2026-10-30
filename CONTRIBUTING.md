# Contributing

Thanks for helping improve Car PhotoMatch.

## Before opening a bug report

Check [Troubleshooting](docs/TROUBLESHOOTING.md). Include:

- Exact **Blender version**, OS and **Car PhotoMatch version**.
- Steps to reproduce and what you expected vs what happened.
- Full Blender console traceback for crashes/errors.
- A minimal `.blend` example only if its models and reference imagery are shareable.

Please do **not** upload photos or car meshes you do not have rights to redistribute.

## Proposing an improvement

Explain the car-matching workflow you want to improve, whether it affects existing saved cameras and what behavior you expect. Small, reproducible feature requests are easiest to evaluate.

## Pull requests

1. Work from the latest source files in `car_photomatch/`.
2. Keep compatibility with Blender 5.2 in mind.
3. Add or update automated tests when possible.
4. Run `python -m unittest discover -s car_photomatch_tests -v` (NumPy required).
5. Smoke-test interactive features in Blender; mocked Python tests cannot validate all Blender UI behavior.
6. Update documentation and version information if behavior changes.

Code is published under **GPL-3.0-or-later**. By contributing, you agree your contribution can be distributed under that license.
