# src/piezo_pic/cells/features/release.py
from __future__ import annotations

from typing import Iterable

import gdsfactory as gf
import numpy as np

from ..tech.layers import LayerMap
from ..tech.params import HoleParams, WaveguideWidths
from ..utils.geometry import min_dist_point_polyline, path_length_um, sample_points_um


# --- module constants (avoid "magic numbers") ---
_DEDUP_TOL_UM = 1e-3
_NUM_EPS = 1e-9
_DIV_EPS = 1e-12


def _dedupe_sorted(vals: np.ndarray, tol: float = _DEDUP_TOL_UM) -> np.ndarray:
    """Return sorted unique values with a tolerance (microns)."""
    if vals.size == 0:
        return vals
    vals = np.sort(vals.astype(float))
    keep: list[float] = [float(vals[0])]
    for v in vals[1:]:
        if abs(float(v) - keep[-1]) > tol:
            keep.append(float(v))
    return np.asarray(keep, dtype=float)


def add_release_rows_at_seams_final_frame(
    comp: gf.Component,
    P: gf.Path,                              # centerline path in final frame
    plate_bbox_xyxy: tuple[float, float, float, float],
    layers: LayerMap,
    holes: HoleParams,
    widths: WaveguideWidths,
    *,
    sample_N: int = 4000,
    straight_tol: float = 0.06,
    bend_trim_um: float = 2.0,              # keep if you plan to use it later; otherwise you can drop it too
    mx_margin: float = 2.0,
    my_margin: float = 2.0,
    pts_final: np.ndarray | None = None,
    x_range: tuple[float, float] | None = None,
    y_range: tuple[float, float] | None = None,
) -> None:
    ...
    """
    Place circular release holes as vertical columns:
      • one at the left inner plate margin,
      • one at the right inner plate margin,
      • and one at the midpoint (in X) between every pair of adjacent **vertical** straights
        of the serpentine (i.e., columns sit BETWEEN the vertical waveguide legs).

    Holes are equispaced vertically and clipped to optional x/y windows.
    The function operates in the component's *final* frame; `rotate_deg` is ignored
    but retained to avoid breaking old call sites.

    Parameters
    ----------
    comp
        Target component to receive hole references.
    P
        Serpentine centerline path (unrotated; already expressed in the same frame as `plate_bbox_xyxy`).
    plate_bbox_xyxy
        Plate bounding box (xmin, ymin, xmax, ymax) in current frame.
    rotate_deg
        Ignored. Present for backward compatibility.
    layers
        LayerMap providing `RELEASE`.
    holes
        Hole parameters (diameter, pitch or rows, optional clearance).
    widths
        Waveguide widths (used for keep-out from SiN core).
    sample_N
        Number of samples used to analyze the path for straight segments.
    straight_tol
        Threshold on |dx/dy| below which a segment is considered vertical.
    bend_trim_um
        Unused; reserved for future edge trimming near bends.
    mx_margin, my_margin
        Inner margins (µm) subtracted from the plate bbox before placing holes.
    pts_final
        Pre-sampled centerline (Nx2) in the current frame (skips sampling if provided).
    x_range, y_range
        Optional clipping windows (xmin, xmax) and (ymin, ymax).

    Returns
    -------
    None
        The function modifies `comp` in place by adding hole references.
    """
    # --- Sample the centerline in the current frame ---
    if pts_final is None:
        s_vals = np.linspace(0.0, float(path_length_um(P)), int(sample_N))
        pts_f = sample_points_um(P, s_vals)
    else:
        pts_f = np.asarray(pts_final, dtype=float)
    if pts_f.shape[0] < 2:
        return

    # --- Detect VERTICAL straights: |dx/dy| small AND |dy|>0 ---
    d = np.diff(pts_f, axis=0)
    dx = d[:, 0]
    dy = d[:, 1]
    inv_slope = np.abs(dx / (np.abs(dy) + _DIV_EPS))  # ~0 for vertical segments
    mask = (inv_slope < float(straight_tol)) & (np.abs(dy) > _NUM_EPS)

    # Group consecutive True's into runs
    runs: list[tuple[int, int]] = []
    i = 0
    N = mask.size
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
    x_centers: list[float] = []
    for i0, i1 in runs:
        seg = pts_f[i0:i1 + 1]
        if seg.shape[0] > 2:
            seg = seg[1:-1]  # soft trim
        if seg.size == 0:
            continue
        x_centers.append(float(seg[:, 0].mean()))
    if len(x_centers) < 2:
        return
    x_centers_arr = np.array(sorted(x_centers), dtype=float)

    # --- Inner "safe" rectangle inside plate margins ---
    xmin, ymin, xmax, ymax = [float(v) for v in plate_bbox_xyxy]
    x0_inner = xmin + float(mx_margin)
    x1_inner = xmax - float(mx_margin)
    y0_inner = ymin + float(my_margin)
    y1_inner = ymax - float(my_margin)
    if x1_inner <= x0_inner or y1_inner <= y0_inner:
        return

    # Apply external clipping windows if provided
    if x_range is not None:
        xr0, xr1 = (float(x_range[0]), float(x_range[1]))
        x0_inner = max(x0_inner, xr0)
        x1_inner = min(x1_inner, xr1)
    if y_range is not None:
        yr0, yr1 = (float(y_range[0]), float(y_range[1]))
        y0_inner = max(y0_inner, yr0)
        y1_inner = min(y1_inner, yr1)
    if x1_inner <= x0_inner or y1_inner <= y0_inner:
        return

    # --- Build column X positions (margins + midpoints BETWEEN vertical legs) ---
    mids = 0.5 * (x_centers_arr[:-1] + x_centers_arr[1:])
    seam_xs = np.concatenate([[x0_inner], mids, [x1_inner]])
    seam_xs = seam_xs[(seam_xs >= x0_inner) & (seam_xs <= x1_inner)]
    seam_xs = _dedupe_sorted(seam_xs, tol=_DEDUP_TOL_UM)
    if seam_xs.size == 0:
        return

    # --- Vertical Y positions: EXCLUDE edge rows ---
    # Option A: explicit rows (holes_per_col)
    if getattr(holes, "holes_per_col", None) is not None:
        Nrows = max(0, int(holes.holes_per_col))
        if Nrows == 0:
            ys = np.array([], dtype=float)
        elif Nrows == 1:
            ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)
        else:
            ys = np.linspace(y0_inner, y1_inner, Nrows + 2, dtype=float)[1:-1]
    else:
        # Option B: pitch (hole_pitch_y_um or hole_pitch_um)
        pitch_y = float((getattr(holes, "hole_pitch_y_um", None) or holes.hole_pitch_um) or 0.0)
        if pitch_y > 0.0:
            y_start = y0_inner + 0.5 * pitch_y
            y_stop = y1_inner - 0.5 * pitch_y
            if y_stop < y_start:
                ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)
            else:
                ys = np.arange(y_start, y_stop + _NUM_EPS, pitch_y, dtype=float)
        else:
            ys = np.array([(y0_inner + y1_inner) * 0.5], dtype=float)

    if ys.size == 0:
        return

    # --- Keep-out from SiN core ---
    avoid_clearance = float(getattr(holes, "avoid_clearance_um", 0.20) or 0.0)
    keepout_um = (float(widths.width_sin_um) / 2.0) + (float(holes.hole_diam_um) / 2.0) + avoid_clearance

    # --- Hole primitive ---
    hole = gf.components.circle(radius=float(holes.hole_diam_um) / 2.0, layer=layers.RELEASE)

    # --- Place holes ---
    for x in seam_xs:
        for y in ys:
            if keepout_um > 0.0:
                dmin = min_dist_point_polyline(float(x), float(y), pts_f)
                if dmin < keepout_um:
                    continue
            ref = comp << hole
            ref.move((float(x), float(y)))
