# src/piezo_pic/features/release.py
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
import gdsfactory as gf

from ..utils.geometry import (
    min_dist_point_polyline,
    path_length_um,
    sample_points_um,
)
from ..tech.layers import LayerMap
from ..tech.params import HoleParams, WaveguideWidths


def _dedupe_sorted(vals: np.ndarray, tol: float = 1e-3) -> np.ndarray:
    """Return sorted unique values with a tolerance (microns)."""
    if vals.size == 0:
        return vals
    vals = np.sort(vals.astype(float))
    keep = [vals[0]]
    for v in vals[1:]:
        if abs(v - keep[-1]) > tol:
            keep.append(v)
    return np.array(keep, dtype=float)


# src/piezo_pic/features/release.py  (only the function below changes)

def add_release_rows_at_seams_final_frame(
    comp: gf.Component,
    P,                                 # gf.Path (unrotated)
    plate_bbox_xyxy: Tuple[float, float, float, float],  # plate bbox in current frame
    rotate_deg: float,                 # kept for API compatibility; ignored
    layers: LayerMap,
    holes: HoleParams,
    widths: WaveguideWidths,
    *,
    sample_N: int = 4000,
    straight_tol: float = 0.06,        # now used as tolerance on |dx/dy| for VERTICAL straights
    bend_trim_um: float = 2.0,
    mx_margin: float = 2.0,
    my_margin: float = 2.0,
    pts_final: Optional[np.ndarray] = None,  # optional pre-sampled centerline (current frame)
) -> None:
    """
    Place release holes as vertical columns:
      • one at the left inner plate margin,
      • one at the right inner plate margin,
      • and one at the midpoint (in X) between every pair of adjacent **vertical** straights
        of the serpentine (so columns sit BETWEEN the vertical waveguide legs, not on them).
    Holes in each column are equispaced vertically.
    """
    # --- Sample the centerline in the current frame ---
    if pts_final is None:
        s_vals = np.linspace(0.0, path_length_um(P), sample_N)
        pts_f = sample_points_um(P, s_vals)
    else:
        pts_f = np.asarray(pts_final, dtype=float)
    if len(pts_f) < 2:
        return

    # --- Detect VERTICAL straights: |dx/dy| small AND |dy|>0 ---
    d  = np.diff(pts_f, axis=0)
    dx = d[:, 0]
    dy = d[:, 1]
    inv_slope = np.abs(dx / (np.abs(dy) + 1e-12))   # ~0 for vertical segments
    mask = (inv_slope < straight_tol) & (np.abs(dy) > 1e-9)

    # Group consecutive True's into runs
    runs, i, N = [], 0, mask.size
    while i < N:
        if mask[i]:
            j = i
            while j < N and mask[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    if not runs:
        return

    # --- Convert runs to vertical straights (trim a bit near bends) ---
    # For vertical straights, X should be ~constant; we take the center X.
    x_centers = []
    for i0, i1 in runs:
        seg = pts_f[i0:i1 + 1]
        # Trim top/bottom ends a little along arclength by dropping a few points
        if len(seg) > 2:
            seg = seg[1:-1]
        if len(seg) == 0:
            continue
        x_centers.append(float(seg[:, 0].mean()))
    if len(x_centers) < 2:
        # Not enough vertical legs to form seams
        return
    x_centers = np.array(sorted(x_centers), dtype=float)

    # --- Inner "safe" rectangle inside plate margins ---
    xmin, ymin, xmax, ymax = plate_bbox_xyxy
    x0 = xmin + mx_margin
    x1 = xmax - mx_margin
    y0 = ymin + my_margin
    y1 = ymax - my_margin
    if x1 <= x0 or y1 <= y0:
        return

    # --- Build column X positions ---
    # Columns at inner margins + midpoints BETWEEN adjacent vertical straights
    mids = 0.5 * (x_centers[:-1] + x_centers[1:])
    seam_xs = np.concatenate([[x0], mids, [x1]])
    # Clip & dedupe for safety
    seam_xs = seam_xs[(seam_xs >= x0) & (seam_xs <= x1)]
    seam_xs = _dedupe_sorted(seam_xs, tol=1e-3)
    if seam_xs.size == 0:
        return

    # --- Vertical Y positions: equispaced by count or pitch ---
    if isinstance(getattr(holes, "holes_per_col", None), int) and holes.holes_per_col > 0:
        ys = np.linspace(y0, y1, holes.holes_per_col)
    else:
        pitch_y = getattr(holes, "hole_pitch_y_um", None) or holes.hole_pitch_um
        if pitch_y and pitch_y > 0:
            ys = np.arange(y0, y1 + 1e-9, pitch_y)
            if ys.size < 2:
                ys = np.linspace(y0, y1, 2)
        else:
            ys = np.linspace(y0, y1, 2)

    # --- Keep-out from SiN core ---
    avoid_clearance = getattr(holes, "avoid_clearance_um", 0.20)
    keepout_um = (widths.width_sin_um / 2.0) + (holes.hole_diam_um / 2.0) + avoid_clearance

    # --- Hole primitive ---
    hole = gf.components.circle(radius=holes.hole_diam_um / 2.0, layer=layers.RELEASE)

    # --- Place holes ---
    for x in seam_xs:
        for y in ys:
            if keepout_um > 0:
                dmin = min_dist_point_polyline(float(x), float(y), pts_f)
                if dmin < keepout_um:
                    continue
            ref = comp << hole
            ref.move((float(x), float(y)))
