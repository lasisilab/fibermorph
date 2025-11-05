# Publishing fibermorph to conda-forge

This guide will help you publish `fibermorph` to conda-forge so users can install it with `conda install -c conda-forge fibermorph`.

## Prerequisites

1. A GitHub account
2. Your package already published on PyPI (✅ done!)
3. Fork the conda-forge/staged-recipes repository

## Steps to publish to conda-forge

### 1. Fork staged-recipes

1. Go to https://github.com/conda-forge/staged-recipes
2. Click "Fork" in the top right
3. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/staged-recipes.git
   cd staged-recipes
   ```

### 2. Create a recipe for fibermorph

1. Create a new branch:
   ```bash
   git checkout -b fibermorph
   ```

2. Copy the example recipe:
   ```bash
   cp -r recipes/example recipes/fibermorph
   ```

3. Edit `recipes/fibermorph/meta.yaml` with this content:

```yaml
{% set name = "fibermorph" %}
{% set version = "0.3.9" %}

package:
  name: {{ name|lower }}
  version: {{ version }}

source:
  url: https://pypi.io/packages/source/{{ name[0] }}/{{ name }}/fibermorph-{{ version }}.tar.gz
  sha256: <GET_THIS_FROM_PYPI>  # See instructions below

build:
  noarch: python
  script: {{ PYTHON }} -m pip install . -vv
  number: 0

requirements:
  host:
    - python >=3.9
    - pip
    - poetry-core <1.9
  run:
    - python >=3.9,<3.14
    - numpy >=1.26.4,<3.0
    - joblib >=1.3.2,<2.0.0
    - pandas >=2.2.0,<3.0.0
    - pillow >=10.2.0,<11.0.0
    - requests >=2.31.0,<3.0.0
    - matplotlib >=3.8.2,<4.0.0
    - rawpy >=0.19.0,<0.20.0
    - scipy >=1.8,<2.0
    - shapely >=2.0.2,<3.0.0
    - argparse >=1.4.0,<2.0.0
    - tqdm >=4.66.1,<5.0.0
    - scikit-image >=0.22.0,<0.23.0
    - scikit-learn >=1.4.0,<2.0.0
    - sympy >=1.12,<2.0
    - pytest >=8.0.0,<9.0.0
    - pyarrow >=15.0.0,<16.0.0

test:
  imports:
    - fibermorph
  commands:
    - fibermorph --help

about:
  home: https://github.com/lasisilab/fibermorph
  summary: 'Toolkit for analyzing hair fiber morphology'
  description: |
    Python package for image analysis of hair curvature and cross-section.
    fibermorph provides tools for automated analysis of fiber morphology
    from microscopy images.
  license: MIT  # Update if your license is different
  license_file: LICENSE
  doc_url: https://github.com/lasisilab/fibermorph
  dev_url: https://github.com/lasisilab/fibermorph

extra:
  recipe-maintainers:
    - tinalasisi  # Your GitHub username
```

### 3. Get the SHA256 hash

1. Go to https://pypi.org/project/fibermorph/0.3.9/#files
2. Click on the `.tar.gz` source distribution
3. Look for "Hashes" and copy the SHA256 value
4. Replace `<GET_THIS_FROM_PYPI>` in the meta.yaml with this hash

### 4. Commit and create Pull Request

```bash
git add recipes/fibermorph
git commit -m "Add fibermorph recipe"
git push origin fibermorph
```

Then:
1. Go to https://github.com/conda-forge/staged-recipes
2. Click "New Pull Request"
3. Select your fork and the `fibermorph` branch
4. Create the PR with title: "Add fibermorph"

### 5. Wait for review and merge

- The conda-forge team will review your recipe (usually takes 1-3 days)
- They may request changes
- Once approved and merged, a new repository will be created: `conda-forge/fibermorph-feedstock`
- Your package will be built and published to conda-forge automatically

### 6. Future updates

After the initial recipe is merged, updates are easier:

1. For each new release on PyPI, create a PR to `conda-forge/fibermorph-feedstock`
2. Update the version and SHA256 in `recipe/meta.yaml`
3. The conda-forge bot can often do this automatically!

## Testing locally before submitting

Before submitting, you can test the recipe locally:

```bash
# Install conda-build
conda install conda-build

# Build the recipe
cd staged-recipes
conda build recipes/fibermorph

# Test the built package
conda install --use-local fibermorph
```

## After conda-forge publication

Users will be able to install with:
```bash
conda install -c conda-forge fibermorph
```

Or add conda-forge to their channels permanently:
```bash
conda config --add channels conda-forge
conda install fibermorph
```

## Resources

- conda-forge documentation: https://conda-forge.org/docs/maintainer/adding_pkgs.html
- Example recipes: https://github.com/conda-forge/staged-recipes/tree/main/recipes
- conda-forge gitter chat: https://gitter.im/conda-forge/conda-forge.github.io

## Notes

- The `noarch: python` setting means one build works for all platforms
- You'll become a maintainer of the feedstock after merge
- You can add CI badges to your README after publication
