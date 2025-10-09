# src/piezo_pic/geometry/serpentine.py
from __future__ import annotations

import gdsfactory as gf

_EULER_ANGLE_DEG = 90
_EPS = 1e-6


def serpentine_path_um(
    iterations: int = 12,
    radius_um: float = 15.0,
    length_um: float = 60.0,
    npts_per_bend: int = 300,
    band_height_um: float | None = None,
    y_margin_um: float = 0.0,
) -> gf.Path:
    """
    Build a centerline serpentine in microns.

    If `band_height_um` is set, the bend radius is clamped so the vertical
    envelope (~ 2*R) fits within `band_height_um - 2*y_margin_um`.
    """
    # validation
    if iterations < 1:
        raise ValueError("iterations must be ≥ 1")
    if radius_um <= 0:
        raise ValueError("radius_um must be > 0")
    if length_um < 0:
        raise ValueError("length_um must be ≥ 0")
    if npts_per_bend < 8:
        raise ValueError("npts_per_bend must be ≥ 8")

    # effective radius (optional band constraint)
    R = float(radius_um)
    if band_height_um is not None:
        usable_h = float(band_height_um) - 2.0 * float(y_margin_um)
        if usable_h <= 0:
            raise ValueError(
                f"band_height_um ({band_height_um}) minus 2*y_margin "
                f"({2*y_margin_um}) must be positive."
            )
        max_R = max(_EPS, 0.5 * usable_h - _EPS)  # enforce 2*R <= usable_h
        R = min(R, max_R)

    # build path
    P = gf.Path()
    for i in range(iterations):
        # alternate +90/-90 each motif to meander
        a1 = +_EULER_ANGLE_DEG if (i % 2 == 0) else -_EULER_ANGLE_DEG
        a2 = -a1
        P += gf.path.euler(radius=R, angle=a1, npoints=npts_per_bend)
        P += gf.path.straight(length=length_um)
        P += gf.path.euler(radius=R, angle=a2, npoints=npts_per_bend)

    return P
