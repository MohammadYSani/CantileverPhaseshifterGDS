from __future__ import annotations
import gdsfactory as gf

def serpentine_path_um(
    iterations: int = 12,
    radius_um: float = 15.0,
    length_um: float = 60.0,
    npts_per_bend: int = 300,
) -> gf.Path:
    """Serpentine centerline in microns: (±90° euler) → straight → (∓90° euler) repeated."""
    P = gf.Path()
    for i in range(iterations):
        a1, a2 = (+90, -90) if i % 2 == 0 else (-90, +90)
        P += gf.path.euler(radius=radius_um, angle=a1, npoints=npts_per_bend)
        P += gf.path.straight(length=length_um)
        P += gf.path.euler(radius=radius_um, angle=a2, npoints=npts_per_bend)
    return P
