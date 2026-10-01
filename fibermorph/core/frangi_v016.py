"""Two-dimensional Frangi vesselness filter exactly as scikit-image 0.16.2 computed it.

Why this module exists
----------------------
The ridge filter is the first step of fibermorph's curvature pipeline: it
turns the grayscale hair image into the map that is thresholded and
skeletonized. The published fibermorph method (Lasisi et al., v0.3.1,
November 2020) used ``skimage.filters.frangi`` from scikit-image 0.16.2.
scikit-image changed that function after 0.16.2, so calling the installed
``skimage.filters.frangi`` no longer reproduces the published numbers:

* the default ``gamma`` changed from 15 to ``None`` (an automatic value
  derived from the image), and
* the Hessian computation changed internally.

With the same fibermorph code, the straight-hair demo image
(``027_demo_nocurv``, 50 px window, 132 px/mm) has a mean curvature of
about 0.053 mm^-1 with scikit-image 0.16.2 and about 0.17 mm^-1 with
scikit-image 0.26, because the Frangi output differs and everything
downstream (threshold, skeleton, Taubin fits) is deterministic given
the Frangi output.

This module freezes the 0.16.2 behavior so that curvature results do not
depend on which scikit-image version is installed. It reproduces the
0.16.2 output to floating-point round-off (about 1e-16) when run on current
NumPy, SciPy and scikit-image. The reference arrays in
``fibermorph/test/test_data/frangi_v016/`` were computed with the real
scikit-image 0.16.2 and are checked in the test suite.

Only the 2-D case with the settings fibermorph uses is provided. The
``alpha`` argument is accepted for signature compatibility but has no effect
in 2-D (the plate-like term is identically 1), as in scikit-image 0.16.2.

Two small helpers are taken from the installed scikit-image instead of being
copied: ``skimage.util.img_as_float`` and ``skimage.util.invert``. For the
images fibermorph passes (8-bit, or float64 in [0, 1]) they return the same
arrays in scikit-image 0.16.2 and 0.26: 8-bit input becomes ``x * (1 / 255)``
as float64 and is inverted as ``255 - x``; float64 input is unchanged and is
inverted as ``1 - x``. ``TestInstalledHelpers`` in
``fibermorph/test/test_frangi_v016.py`` checks exactly this, so a future
scikit-image that changes either helper is reported by name.

License
-------
This code is derived from ``skimage/filters/ridges.py`` and
``skimage/feature/corner.py`` of scikit-image 0.16.2, which is distributed
under the BSD 3-Clause license. The copyright notice and license text
required by that license follow.

    Copyright (C) 2019, the scikit-image team
    All rights reserved.

    Redistribution and use in source and binary forms, with or without
    modification, are permitted provided that the following conditions are
    met:

     1. Redistributions of source code must retain the above copyright
        notice, this list of conditions and the following disclaimer.
     2. Redistributions in binary form must reproduce the above copyright
        notice, this list of conditions and the following disclaimer in
        the documentation and/or other materials provided with the
        distribution.
     3. Neither the name of skimage nor the names of its contributors may be
        used to endorse or promote products derived from this software
        without specific prior written permission.

    THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
    IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
    WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
    INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
    (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
    HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
    STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
    IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
    POSSIBILITY OF SUCH DAMAGE.

Reference: Frangi AF, Niessen WJ, Vincken KL, Viergever MA (1998).
Multiscale vessel enhancement filtering. MICCAI, pp. 130-137.
"""

from itertools import combinations_with_replacement

import numpy as np
from scipy import ndimage as ndi
from skimage.util import img_as_float, invert

__all__ = ["frangi_v016"]


def _divide_nonzero(array1, array2, cval=1e-10):
    """Divide ``array1`` by ``array2``, replacing zero denominators by ``cval``."""
    denominator = np.copy(array2)
    denominator[denominator == 0] = cval
    return np.divide(array1, denominator)


def _hessian_eigvals_v016(image, sigma):
    """Scale-normalized Hessian eigenvalues of a 2-D image, sorted by absolute value.

    Follows ``compute_hessian_eigenvalues(image, sigma, sorting='abs')`` of
    scikit-image 0.16.2: Gaussian smoothing with zero padding at the border
    (``mode='constant', cval=0``), second derivatives from repeated
    ``np.gradient``, multiplication by ``sigma ** 2``, closed-form eigenvalues
    of the symmetric 2x2 matrix, then ordering by increasing absolute value.

    Returns an array of shape ``(2,) + image.shape``; index 0 holds the
    eigenvalue with the smaller absolute value.
    """
    image = img_as_float(image)

    gaussian_filtered = ndi.gaussian_filter(image, sigma=sigma, mode="constant", cval=0)
    gradients = np.gradient(gaussian_filtered)

    axes = reversed(range(image.ndim))  # order='rc'
    h_elems = [
        np.gradient(gradients[ax0], axis=ax1)
        for ax0, ax1 in combinations_with_replacement(axes, 2)
    ]
    h_elems = [(sigma ** 2) * e for e in h_elems]  # correct for scale

    m00, m01, m11 = h_elems
    half_trace = (m00 + m11) / 2
    half_gap = np.sqrt(4 * m01 ** 2 + (m00 - m11) ** 2) / 2
    eigenvalues = np.array([half_trace + half_gap, half_trace - half_gap])

    order = np.abs(eigenvalues).argsort(axis=0)
    return np.take_along_axis(eigenvalues, order, axis=0)


def frangi_v016(image, sigmas=range(1, 10, 2), alpha=0.5, beta=0.5, gamma=15,
                black_ridges=True):
    """Frangi vesselness filter of a 2-D image, as in scikit-image 0.16.2.

    Parameters
    ----------
    image : (N, M) ndarray
        Input image (the fibermorph pipeline passes an 8-bit grayscale image).
    sigmas : iterable of float, optional
        Gaussian scales; the output is the per-pixel maximum over scales.
    alpha : float, optional
        Accepted for compatibility with ``skimage.filters.frangi``; unused in 2-D.
    beta : float, optional
        Sensitivity to deviation from a blob-like structure.
    gamma : float, optional
        Sensitivity to areas of high structure. scikit-image 0.16.2 used the
        fixed default 15; newer scikit-image versions compute it from the
        image when it is ``None``, which is the main source of the change in
        results that this module avoids.
    black_ridges : bool, optional
        If True (default), detect dark ridges on a light background, which is
        how hairs appear in fibermorph's curvature images.

    Returns
    -------
    out : (N, M) ndarray of float64
        Filtered image (maximum over scales), identical to the output of
        ``skimage.filters.frangi`` in scikit-image 0.16.2.
    """
    image = np.asarray(image)
    if image.ndim != 2:
        raise ValueError(
            f"frangi_v016 expects a 2-D image, got an array with {image.ndim} dimension(s)"
        )

    sigmas = np.asarray(sigmas)
    if np.any(sigmas < 0.0):
        raise ValueError("Sigma values less than zero are not valid")

    beta_sq = 2 * beta ** 2
    gamma_sq = 2 * gamma ** 2

    # Invert the image to detect dark ridges on a light background
    if black_ridges:
        image = invert(image)

    filtered_array = np.zeros(sigmas.shape + image.shape)
    lambdas_array = np.zeros(sigmas.shape + image.shape)

    for i, sigma in enumerate(sigmas):
        lambda1, lambda2 = _hessian_eigvals_v016(image, sigma)

        # Sensitivity to deviation from a blob-like structure (eq. 10 and 15 in
        # Frangi et al.); np.abs(lambda2) in 2-D
        r_b = _divide_nonzero(lambda1, np.abs(lambda2)) ** 2

        # Sensitivity to areas of high structure (eq. 12)
        r_g = lambda1 ** 2 + lambda2 ** 2

        # The plate-like term (1 - exp(-r_a / alpha_sq)) equals 1 in 2-D
        # because r_a is infinite there.
        filtered_array[i] = np.exp(-r_b / beta_sq) * (1 - np.exp(-r_g / gamma_sq))
        lambdas_array[i] = lambda2

    # Remove background
    filtered_array[lambdas_array > 0] = 0

    return np.max(filtered_array, axis=0)
