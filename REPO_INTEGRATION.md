# ReachScan repository integration

This directory is intended to be unpacked at the root of the public `reachscan` GitHub repository.

## Commit to normal Git history

Commit the software and documentation contained here:

- `src/`, `tests/`, `examples/`, and `notebooks/`
- `pyproject.toml`, `ruff.toml`, `.github/`, and `.gitignore`
- `README.md`, `CHANGELOG.md`, `CITATION.cff`, `.zenodo.json`, and licenses
- `docs/`, `archive/`, `release_assets/`, and `scripts/verify_release_assets.py`

## Do not commit to normal Git history

Do not add the 131 MiB evidence archive or the optional historical volumes to ordinary Git history. Publish them as Zenodo records and/or GitHub Release assets, then replace the placeholder identifiers in `docs/PRODUCT_ARCHITECTURE.md` and `archive/README.md`.

## Current release family

- Core Research Article: v1.0-RC8
- Supplementary Evidence Appendix: v1.0-RC8
- Full Technical Report and Audit Record: v0.9.34
- Reach-Scan Evidence and Reproducibility Archive: v1.0-RC2
- `reachscan` software: v0.2.2
- Historical lineage volumes: v1.0-RC1, optional and unchanged

## First push

```bash
git init
git add .
git commit -m "Initial public release of reachscan v0.2.2"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

Then create a Git tag and GitHub release:

```bash
git tag -a v0.2.2 -m "reachscan v0.2.2"
git push origin v0.2.2
```

Attach the paper PDFs only if desired. The canonical evidence archive should be deposited separately and cited by DOI.
