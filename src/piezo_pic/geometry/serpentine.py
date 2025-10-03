# src/piezo_pic/geometry/serpentine.py
from __future__ import annotations
import gdsfactory as gf


def serpentine_path_um(
    iterations: int = 12,
    radius_um: float = 15.0,
    length_um: float = 60.0,
    npts_per_bend: int = 300,
    band_height_um: float | None = None,   # optional vertical constraint
    y_margin_um: float = 0.0,              # equal top/bottom margin inside the band
) -> gf.Path:
    """
    Build a centerline serpentine in microns:

        [ +90° euler ] → [ straight ] → [ -90° euler ]
        [ -90° euler ] → [ straight ] → [ +90° euler ]
        ...repeat for `iterations`

    If `band_height_um` is set, we limit the meander height by clamping the
    bend radius to fit inside (band_height_um - 2*y_margin_um).
    """

    # --- lightweight validation ---
    if iterations < 1:
        raise ValueError("iterations must be ≥ 1")
    if radius_um <= 0:
        raise ValueError("radius_um must be > 0")
    if length_um < 0:
        raise ValueError("length_um must be ≥ 0")
    if npts_per_bend < 8:
        raise ValueError("npts_per_bend must be ≥ 8")

    # --- choose effective bend radius ---
    R = float(radius_um)
    if band_height_um is not None:
        usable_H = float(band_height_um) - 2.0 * float(y_margin_um)
        if usable_H <= 0:
            raise ValueError(
                f"band_height_um ({band_height_um}) minus 2*y_margin "
                f"({2*y_margin_um}) must be positive."
            )
        # For a meander built from 90° bends, the vertical envelope ≈ 2*R.
        # Clamp R so 2*R <= usable_H (leave a tiny epsilon).
        max_R = max(1e-6, 0.5 * usable_H - 1e-6)
        R_eff = min(R, max_R)
        if R_eff < R:
            # We reduced the radius to make the path fit the requested band.
            R = R_eff

    # --- build the meander with the effective radius ---
    P = gf.Path()
    for i in range(iterations):
        # Alternate the bend sense each motif so the path meanders
        a1, a2 = (+90, -90) if (i % 2 == 0) else (-90, +90)
        P += gf.path.euler(radius=R, angle=a1, npoints=npts_per_bend)
        P += gf.path.straight(length=length_um)
        P += gf.path.euler(radius=R, angle=a2, npoints=npts_per_bend)

    # Note: by construction (alternating +90/-90 with radius R),
    # the path's bbox height will be ≈ 2*R. No extra scaling/translation needed.

    return P
