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
    straight_tol: float = 0.06,        # tolerance on |dx/dy| for VERTICAL straights
    bend_trim_um: float = 2.0,
    mx_margin: float = 2.0,
    my_margin: float = 2.0,
    pts_final: Optional[np.ndarray] = None,  # optional pre-sampled centerline (current frame)
    x_range: Optional[Tuple[float, float]] = None,       # allowed X window for holes
    y_range: Optional[Tuple[float, float]] = None,       # allowed Y window for holes
) -> None:
    """
    Place release holes as vertical columns:
      • one at the left inner plate margin,
      • one at the right inner plate margin,
      • and one at the midpoint (in X) between every pair of adjacent **vertical** straights
        of the serpentine (so columns sit BETWEEN the vertical waveguide legs).
    Holes are equispaced vertically. Optional x_range/y_range clip the placement window.
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

    # --- Convert runs to vertical straights (trim ends a little) ---
    x_centers = []
    for i0, i1 in runs:
        seg = pts_f[i0:i1 + 1]
        if len(seg) > 2:
            seg = seg[1:-1]
        if len(seg) == 0:
            continue
        x_centers.append(float(seg[:, 0].mean()))
    if len(x_centers) < 2:
        return
    x_centers = np.array(sorted(x_centers), dtype=float)

    # --- Inner "safe" rectangle inside plate margins ---
    xmin, ymin, xmax, ymax = plate_bbox_xyxy
    x0_inner = xmin + mx_margin
    x1_inner = xmax - mx_margin
    y0_inner = ymin + my_margin
    y1_inner = ymax - my_margin
    if x1_inner <= x0_inner or y1_inner <= y0_inner:
        return

    # Apply external clipping windows if provided
    if x_range is not None:
        xr0, xr1 = x_range
        x0_inner = max(x0_inner, xr0)
        x1_inner = min(x1_inner, xr1)
    if y_range is not None:
        yr0, yr1 = y_range
        y0_inner = max(y0_inner, yr0)
        y1_inner = min(y1_inner, yr1)
    if x1_inner <= x0_inner or y1_inner <= y0_inner:
        return

    # --- Build column X positions (margins + midpoints BETWEEN vertical legs) ---
    mids = 0.5 * (x_centers[:-1] + x_centers[1:])
    seam_xs = np.concatenate([[x0_inner], mids, [x1_inner]])
    seam_xs = seam_xs[(seam_xs >= x0_inner) & (seam_xs <= x1_inner)]
    seam_xs = _dedupe_sorted(seam_xs, tol=1e-3)
    if seam_xs.size == 0:
        return

    # --- Vertical Y positions: EXCLUDE edge rows ---
    if isinstance(getattr(holes, "holes_per_col", None), int) and holes.holes_per_col is not None:
        Nrows = max(0, int(holes.holes_per_col))
        if Nrows == 0:
            ys = np.array([], dtype=float)
        elif Nrows == 1:
            ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)
        else:
            # exclude edges by padding by one and slicing out first/last
            ys = np.linspace(y0_inner, y1_inner, Nrows + 2, dtype=float)[1:-1]
    else:
        pitch_y = float((getattr(holes, "hole_pitch_y_um", None) or holes.hole_pitch_um) or 0.0)
        if pitch_y > 0.0:
            # center the grid between the edges so no row is on the boundary
            y_start = y0_inner + 0.5 * pitch_y
            y_stop  = y1_inner - 0.5 * pitch_y
            if y_stop < y_start:
                # not enough room for one full pitch: place one row in the middle
                ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)
            else:
                # include end if within a tiny tolerance
                ys = np.arange(y_start, y_stop + 1e-9, pitch_y, dtype=float)
        else:
            # fallback: one row in the middle (still avoids edges)
            ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)

    if ys.size == 0:
        return

    # --- Keep-out from SiN core ---
    avoid_clearance = float(getattr(holes, "avoid_clearance_um", 0.20) or 0.0)
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
