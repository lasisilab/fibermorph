## Dependency Slimming Plan

We want to reduce install and deployment overhead (for both the CLI and the Streamlit GUI) by auditing fibermorph's dependencies. This document outlines the plan, rationale, and checklist so the work stays organized.

### Goals
- Identify runtime dependencies that are no longer required for core workflows.
- Move optional functionality (GUI, raw conversion, demo generators) behind extras.
- Keep the base install as lightweight as possible (numpy, scipy, scikit-image, pandas, joblib, tqdm).
- Record every change/rationale here for future reference.

### Candidate Dependencies

| Package       | Current Usage | Proposed Action | Notes |
|---------------|---------------|-----------------|-------|
| `sympy`       | Dummy data ellipse area | Replace with `math.pi * a * b`; remove dependency | Not used in runtime workflows |
| `matplotlib`  | Historical plotting/demos | Confirm active usage; move to optional extra if only for visualization | GUI doesn't rely on it |
| `pyarrow`     | Legacy | Verify actual usage; drop if unused | Listed in deps but not obviously referenced |
| `rawpy`       | `--raw2gray` workflow | Move to optional `raw` extra; guard import | GUI users typically upload TIFFs |
| `scikit-learn`| Dummy data MinMaxScaler | Swap for numpy-based scaling; remove dependency | Not needed elsewhere |
| `shapely`     | Dummy data ellipse properties | Replace with basic geometry math | Avoid heavy dep |
| `pytest`      | Should be dev-only | Ensure not bundled into runtime distribution | Already in dev group but reconfirm |
| GUI extras    | `streamlit`, `requests` | Already optional via `[gui]` extra | Keep optional |

### Audit Checklist
1. **Inventory imports** – run `python tools/inventory_imports.py` to map modules → files.
2. **Evaluate usage** – verify whether each package is required at runtime/tests or just demos.
3. **Refactor replacements**:
   - Update `demo/dummy_data.py` to remove `sympy`, `scikit-learn`, `shapely` usage.
   - Confirm whether any modules still need `matplotlib`.
4. **Update `pyproject.toml`**:
   - Remove trimmed packages from `[tool.poetry.dependencies]`.
   - Add extras (e.g., `raw = ["rawpy"]`, `viz = ["matplotlib"]`).
5. **Guard optional imports** – wrap optional features with lazy imports/try-except.
6. **Docs** – update README/CHANGELOG to describe new extras and lighter core install.
7. **Testing** – run pytest with minimal install; run GUI smoke test with relevant extras.

### Next Steps
- Work on a dedicated branch (e.g., `feature/dependency-trim`) branched from `main`.
- Tackle the checklist, updating this document with decisions/results.
- Once complete, bump version and summarize changes.

### Tools
- `python tools/inventory_imports.py` – reports top-level imports across the `fibermorph` package.
