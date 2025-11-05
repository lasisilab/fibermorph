## Dependency Slimming Plan

We want to reduce install and deployment overhead (for CLI users and the Streamlit GUI) by auditing fibermorph's dependencies. Below is the proposed plan including rationale and tasks.

### Goals
- Identify runtime dependencies currently imported but not needed for core workflows.
- Move optional features (GUI, raw image conversion, demo generators) behind extras.
- Keep core install lightweight (focus on numpy/scipy/scikit-image/pandas/joblib/tqdm).
- Document decisions and follow-up actions here for traceability.

### Key Targets

| Package       | Current Usage | Proposed Action | Notes |
|---------------|---------------|-----------------|-------|
| `sympy`       | Dummy data ellipse area | Replace with `math.pi * a * b`; remove dependency | No runtime reliance in workflows/GUI |
| `matplotlib`  | Possibly unused in production; historical plotting | Confirm actual usage; if only demos/legacy, move to optional extra | Remove from core if safe |
| `pyarrow`     | Possibly legacy | Verify if Arrow/Parquet output still needed; drop if unused | Mentioned in deps but not clearly referenced |
| `rawpy`       | Only for raw conversions (`--raw2gray`) | Move to optional extra `raw`; add guard around import | GUI users typically work with TIFF |
| `scikit-learn`| Dummy data scaling | Replace with numpy-based scaling; drop dependency | Currently used in `dummy_data.py` |
| `shapely`     | Dummy data ellipse calculations | Replace with simple geometry math; remove dependency | Not required for analysis |
| `pytest`      | Should be dev-only | Ensure no runtime dependency, keep in dev group | Already in dev group but double-check packaging metadata |
| GUI extras    | `streamlit`, `requests` | Already optional via `[gui]`; confirm no accidental core imports | Keep optional |

### Audit Checklist
1. **Inventory imports**: generate top-level import list (`python tools/inventory_imports.py`).
2. **Evaluate necessity**: for each dependency, confirm if used in runtime, tests, or demos.
3. **Refactor replacements**:
   - Replace `sympy`, `scikit-learn`, `shapely` usage in `dummy_data.py`.
   - Ensure no modules implicitly require matplotlib.
4. **Update `pyproject.toml`**:
   - Remove trimmed deps from `[tool.poetry.dependencies]`.
   - Add extras: e.g. `raw = ["rawpy"]`, `viz = ["matplotlib"]`.
   - Keep GUI extras (`streamlit`, `requests`) optional.
5. **Guard optional features** with lazy imports/try-except.
6. **Documentation**:
   - Update README to describe optional extras for raw conversions / GUI / viz.
7. **Testing**:
   - Run pytest with minimal dependencies.
   - Run GUI smoke test with new extras.

### Next Steps
- Create a branch off main (e.g., `feature/dependency-trim`) for this work.
- Execute audit checklist, recording decisions/renovations here.
- After trimming, bump package version and update changelog/release notes.

### Tools
- `python tools/inventory_imports.py` — quick import inventory across `fibermorph` package.
