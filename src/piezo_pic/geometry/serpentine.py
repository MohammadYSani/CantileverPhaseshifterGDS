# src/piezo_pic/geometry/serpentine.py
from __future__ import annotations
import gdsfactory as gf


def serpentine_path_um(
    iterations: int = 12,
    radius_um: float = 15.0,
    length_um: float = 60.0,
    npts_per_bend: int = 300,
) -> gf.Path:
    """
    Build a centerline serpentine in microns:

        [ +90° euler ] → [ straight ] → [ -90° euler ]
        [ -90° euler ] → [ straight ] → [ +90° euler ]
        ...repeat for `iterations`

    Parameters
    ----------
    iterations : int
        Number of bend–straight “motifs” to place (must be ≥1).
    radius_um : float
        Euler bend radius in µm (must be >0).
    length_um : float
        Straight length between bends in µm (must be ≥0).
    npts_per_bend : int
        Polygon sampling points per bend (≥8 recommended).

    Returns
    -------
    gf.Path
        The assembled centerline path (units: µm).
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

    P = gf.Path()
    for i in range(iterations):
        # Alternate the bend sense each motif so the path meanders
        a1, a2 = (+90, -90) if (i % 2 == 0) else (-90, +90)
        P += gf.path.euler(radius=radius_um, angle=a1, npoints=npts_per_bend)
        P += gf.path.straight(length=length_um)
        P += gf.path.euler(radius=radius_um, angle=a2, npoints=npts_per_bend)
    return P
