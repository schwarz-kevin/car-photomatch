# How to publish Car PhotoMatch on GitHub

The repository package includes **both** editable source and a **Blender-installable ZIP**. GitHub does **not** automatically extract a ZIP that you upload as a single file into a repository. Follow the steps below to show the readable source and docs on GitHub.

## Publish with the GitHub website (no Git commands)

1. **Extract** the outer `car_photomatch_github_v0_3_1.zip` on your computer.
2. On GitHub, create a new repository (for example `car-photomatch`). Choose an empty repository to avoid unnecessary merge steps.
3. Open the repository page and choose **Add file → Upload files**.
4. Upload the **contents of the extracted folder** (including `.github`, `docs`, `car_photomatch`, `car_photomatch_tests`, `releases`, `README.md`, `LICENSE`). Some browsers hide dot-folders; verify that `.github` was included.
5. Commit the files. `README.md` becomes your repository homepage and links to tutorials and the prebuilt ZIP.
6. Optionally choose **Releases → Draft a new release**, tag `v0.3.1`, and attach the existing `releases/car_photomatch_0_3_1.zip` as the release binary. Explain that users should install **this** ZIP, not GitHub's automatically generated **Source code (zip)**.
7. Update the maintainer/author name and repository URL wherever you want your chosen public identity to appear. The current metadata uses the generic project name `Car PhotoMatch Project`.

GitHub's [file-upload guide](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository) describes the browser workflow.

## Publish with Git (recommended for updates)

Run in the **extracted repository root**. Replace `YOUR_ACCOUNT` with your actual GitHub username or organization and create an empty repo on GitHub first.

```bash
git init
git add .
git commit -m "Initial public release: Car PhotoMatch v0.3.1"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/car-photomatch.git
git push -u origin main
```

Then create the `v0.3.1` release and attach **`releases/car_photomatch_0_3_1.zip`**. A Release binary is clearer for end users than asking them to download the entire project.

## Release checklist

- [ ] Verify LICENSE and maintainership information.
- [ ] Run automated tests: `python -m unittest discover -s car_photomatch_tests -v`.
- [ ] Test installation and the main photomatching workflow in Blender 5.2.
- [ ] Confirm the extension archive has `blender_manifest.toml` at its root.
- [ ] Create Git tag and GitHub Release for the version.
- [ ] Attach the **extension ZIP** and provide install steps.
- [ ] Keep the version in `blender_manifest.toml`, add-on `bl_info`, changelog and archive filename in sync for future versions.

**License note:** The existing add-on source declares `GPL-3.0-or-later`. The repository includes the matching GPLv3 license text. If you distribute modified versions, follow the relevant GPL obligations.
