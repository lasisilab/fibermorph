# Contributing to fibermorph

Thanks for contributing! A couple of conventions keep the project tidy.

## Branching model

- **`main`** is the released / public branch — what `pip install fibermorph`
  ships and what the Streamlit Cloud app deploys. It only advances when a
  maintainer promotes `fibermorph-dev` after review. **Please don't target
  `main` in pull requests.**
- **`fibermorph-dev`** is the integration branch where all new work lands.
  **Open your pull requests against `fibermorph-dev`.**

## Start from the latest `fibermorph-dev`

Build on the current code so your work sits on top of the latest changes:

```bash
git remote add upstream https://github.com/lasisilab/fibermorph.git   # once
git fetch upstream
git checkout -b my-feature upstream/fibermorph-dev
```

## Development setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate   # Python 3.10–3.12
pip install -e '.[gui]'      # editable install with the GUI extra
pytest                       # run the test suite
fibermorph-gui               # launch the GUI locally
```

## Pull requests

- **Target `fibermorph-dev`.**
- Use a **Conventional Commits** PR title — the `title-format` CI check requires
  one. Start with a type: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
  `chore:`, `ci:`, etc. Example: `feat: validate wave-count on synthetic fibers`.
- Make sure `pytest` passes before requesting review.

## Releases (maintainers)

Bump `version` in `pyproject.toml`, commit, then tag:

```bash
git tag vX.Y.Z && git push origin vX.Y.Z
```

The `Release` workflow builds and publishes to PyPI via Trusted Publishing.
See [ROADMAP.md](ROADMAP.md) and [CHANGELOG.md](CHANGELOG.md) for context.
