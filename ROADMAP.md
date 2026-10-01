# fibermorph roadmap

Planned work and known follow-ups that aren't discrete GitHub issues yet. For
shipped changes see [CHANGELOG.md](CHANGELOG.md); for bugs/features, open an
issue on [lasisilab/fibermorph](https://github.com/lasisilab/fibermorph/issues).

**Status (2026-07-04):** the working line is **2.0.0** on the `fibermorph-dev`
branch. The published PyPI release is **1.0.1**. 2.0.0 is not yet tagged or
published.

---

## Before the next release
- [ ] Merge `fibermorph-dev` → `main`, then cut the release. Decide the version:
      fold the `[Unreleased]` changes into 2.0.0, or tag a new number.
- [ ] Releasing is automated: bump `version` in `pyproject.toml`, commit, then
      `git tag vX.Y.Z && git push origin vX.Y.Z` — the `Release` workflow
      (`.github/workflows/publish.yml`) builds and publishes via PyPI Trusted
      Publishing.
- [ ] **Verify PyPI Trusted Publishing is configured** for the repo and the
      `pypi` GitHub environment before the first 2.0.0 publish, or the publish
      step will fail.
- [ ] Regenerate `poetry.lock` if dependencies changed.

## Curvature science — validate before trusting
- Extended curvature metrics (curl index, wave count) and CLAHE preprocessing
  were removed from curvature: neither is part of the published method (see
  [CHANGELOG.md](CHANGELOG.md)). Any curvature metric added in future has to be
  validated against the published method before it ships.
- [ ] **Diameter** was removed (not trusted). Revisit a medial-axis / skeleton
      diameter once the method is validated.
- [ ] **Large curvature images (multi-GB):** investigate *safe* downsampling.
      Small fragments can merge or vanish and shift curvature, so this needs a
      measured study first. (Cross-section already auto-downsamples to a target
      working resolution; curvature does not.)

## GUI polish (design follow-ups)
- [ ] Custom results table with in-cell **Method pills** (currently `st.dataframe`
      with a restyled header).
- [ ] Custom **input bar** matching the design mock (currently the stock uploader
      plus the Settings card).

## Tech debt & testing
- [ ] `fibermorph/gui/visualizations.py` (~650 lines) is **orphaned** — never
      imported. Either wire it into a results/figures view or remove it.
- [ ] Retire the `fibermorph.fibermorph` / `fibermorph.fibermorph_compat`
      backward-compatibility shims when the deprecation window closes.
- [ ] Add tests for currently-untested modules: `cli.py` (arg parsing + the new
      unit conversion), `utils/imaging.py` (downsampling measurement invariance,
      &lt;0.5%), `gui/launcher.py`, `processing/section_sam2.py` (checkpoint
      resolution + watershed fallback), `demo/demo.py` (remote-data error paths).
- [ ] Extend resolution-aware downsampling to the **batch/CLI section path**
      (verify classical Chan-Vese invariance first).

## Documentation
- [ ] A **column reference** for the `--extended-features` output CSVs (which
      columns the flag adds).
- [ ] A short **CONTRIBUTING / developer setup** guide (this file plus the
      "Run locally from source" section of the README are a starting point).

## Student follow-ups (file as GitHub issues)
File one issue per finding on `lasisilab/fibermorph`, each with file:line
references and acceptance criteria:
- [ ] SAM2 reachability / config-default handling for `--use-sam2`.
