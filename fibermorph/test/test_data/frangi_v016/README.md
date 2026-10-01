# Reference data for the frozen Frangi filter

`fibermorph/core/frangi_v016.py` reproduces `skimage.filters.frangi` as it was in
scikit-image 0.16.2 (the version behind the published fibermorph results).
`fibermorph/test/test_frangi_v016.py` checks it against the arrays in this folder.

| File | Content |
|---|---|
| `input_uint8.npy` | 64 x 96 8-bit test image: a dark arc cut by the border, a diagonal line, a short thick segment, mild noise (seeded). |
| `ref_default.npy` | `skimage.filters.frangi(input_uint8)` |
| `ref_float64.npy` | `skimage.filters.frangi(input_uint8 / 255.0)` |
| `ref_white_sigmas.npy` | `skimage.filters.frangi(input_uint8, sigmas=[1, 2, 3.5], black_ridges=False)` |
| `make_frangi_reference.py` | Writes all of the above. |

## How the references were made

With scikit-image **0.16.2** (Python 3.8.20, numpy 1.18.5, scipy 1.4.1), run as
x86_64 on Apple silicon:

```
cd fibermorph/test/test_data/frangi_v016
arch -x86_64 <paper-era env>/bin/python make_frangi_reference.py
```

The script refuses to run with any other scikit-image version. The installed
scikit-image of a current environment gives a different result for the same
input (largest difference about 0.85 against a reference maximum of 1.9e-4),
which is what the test detects.
