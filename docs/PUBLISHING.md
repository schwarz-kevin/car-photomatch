# GitHub release publishing — update from v0.3.1 to v0.4.12

Keep your existing repository, local `.git` directory, history and v0.3.1 release. No new repository is needed.

## Update source in your local clone (Windows 11)

1. Back up the existing clone, and run `git status` in it to check for uncommitted changes.
2. Run `git pull --ff-only origin main` to retrieve any changes from GitHub.
3. Copy the **contents** of the supplied v0.4.12 GitHub-update package into the **root** of your existing local `car-photomatch` folder. Accept replacement of source/docs/tests. **Do not delete or replace the `.git` folder**; it is not included in this package.
4. If you personally edited README or docs since the last package, merge those edits rather than overwriting them blindly.
5. Run:

```bash
git status
git add .
git commit -m "Release Car PhotoMatch v0.4.12"
git push origin main
```

## Publish v0.4.12

1. Open `https://github.com/schwarz-kevin/car-photomatch/releases/new`.
2. Choose tag **v0.4.12**, Target **main** (after pushing), title **Car PhotoMatch v0.4.12**.
3. Attach **`car_photomatch_0_4_12_ui_workflow.zip`** from `releases/` under *Attach binaries*. This is the Blender installer, not GitHub Source code ZIP.
4. Mark **Pre-release**, because Rim PhotoMatch remains experimental, and publish.
5. Verify that the asset downloads and the README points to it.

The original v0.3.1 release stays available. `main` and latest source are at 0.4.12 after the push. The `latest` badge may continue to point to stable v0.3.1 while v0.4.12 is marked as a pre-release.
