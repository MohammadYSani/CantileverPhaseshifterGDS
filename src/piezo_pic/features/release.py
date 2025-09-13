# src/piezo_pic/features/release.py
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np
import gdsfactory as gf

from ..utils.geometry import (
    rotate_xy,
    min_dist_point_polyline,
)
from ..tech.layers import LayerMap
from ..tech.params import HoleParams, WaveguideWidths


def add_release_rows_at_seams_final_frame(
    comp: gf.Component,
    P,                                 # gf.Path (unrotated)
    plate_bbox_xyxy: Tuple[float, float, float, float],  # FINAL frame bbox
    rotate_deg: float,
    layers: LayerMap,
    holes: HoleParams,
    widths: WaveguideWidths,
    *,
    sample_N: int = 4000,
    straight_tol: float = 0.06,
    bend_trim_um: float = 2.0,
    mx_margin: float = 2.0,
    my_margin: float = 2.0,
    pts_final: Optional[np.ndarray] = None,  # pre-rotated sample passed in? (FINAL frame)
) -> None:
    """
    Place *rows* of circular release holes centered between adjacent straight
    segments of the serpentine *in the FINAL frame* (after rotation).
    Keeps a radial clearance from the SiN core.

    Notes
    -----
    - "straight" detection: slope < straight_tol and |dx|>0 on sampled points
    - rows span the plate's inner margin box (edge margins mx/my)
    - if `holes.holes_per_row` is an int > 0, place exactly that many per row;
      otherwise use `holes.hole_pitch_um` as uniform step.
    """
    # --- Sample the centerline and rotate to FINAL frame ---
    if pts_final is None:
        try:
            s_vals = np.linspace(0.0, float(P.length()), sample_N)
            pts = P.sample(s_vals)
        except Exception:
            pts0 = np.asarray(P.points)
            if len(pts0) < 2:
                return
            seg = np.sqrt(np.sum(np.diff(pts0, axis=0) ** 2, axis=1))
            s_cum = np.concatenate([[0.0], np.cumsum(seg)])
            s_vals = np.linspace(0.0, s_cum[-1], sample_N)
            x = np.interp(s_vals, s_cum, pts0[:, 0])
            y = np.interp(s_vals, s_cum, pts0[:, 1])
            pts = np.column_stack([x, y])
        pts_f = rotate_xy(pts, rotate_deg)
    else:
        pts_f = np.asarray(pts_final)

    if len(pts_f) < 2:
        return

    # --- Detect "straight" runs (|dy/dx| small AND |dx|>0) ---
    d = np.diff(pts_f, axis=0)
    dx, dy = d[:, 0], d[:, 1]
    slope = np.abs(dy / (np.abs(dx) + 1e-12))
    mask = (slope < straight_tol) & (np.abs(dx) > 1e-9)

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
    if len(runs) < 2:
        return

    # --- Convert runs to usable straight spans with bend trimming ---
    straights = []
    for i0, i1 in runs:
        seg_pts = pts_f[i0:i1 + 1]
        x_min = float(seg_pts[:, 0].min()) + bend_trim_um
        x_max = float(seg_pts[:, 0].max()) - bend_trim_um
        y_mean = float(seg_pts[:, 1].mean())
        if x_max > x_min:
            straights.append((x_min, x_max, y_mean))
    if len(straights) < 2:
        return

    # --- Inner "safe" rectangle inside plate margins ---
    xmin, ymin, xmax, ymax = plate_bbox_xyxy
    x0 = xmin + mx_margin
    x1 = xmax - mx_margin
    y0 = ymin + my_margin
    y1 = ymax - my_margin
    if x1 <= x0 or y1 <= y0:
        return

    # --- Waveguide keep-out radius ---
    # Use holes.avoid_clearance_um if present; else default to 0.20 µm
    avoid_clearance = getattr(holes, "avoid_clearance_um", 0.20)
    keepout_um = (widths.width_sin_um / 2.0) + (holes.hole_diam_um / 2.0) + avoid_clearance

    # --- Hole primitive on release layer ---
    hole = gf.components.circle(radius=holes.hole_diam_um / 2.0, layer=layers.RELEASE)

    # --- For each pair of adjacent straights, place a row halfway in Y ---
    for k in range(len(straights) - 1):
        _, _, y0s = straights[k]
        _, _, y1s = straights[k + 1]
        y_mid = 0.5 * (y0s + y1s)
        if not (y0 <= y_mid <= y1):
            continue

        if isinstance(holes.holes_per_row, int) and holes.holes_per_row > 0:
            xs = np.linspace(x0, x1, holes.holes_per_row)
        else:
            xs = np.arange(x0, x1 + 1e-9, holes.hole_pitch_um)

        for x in xs:
            # Honor keep-out from the SiN centerline
            if keepout_um > 0:
                dmin = min_dist_point_polyline(float(x), float(y_mid), pts_f)
                if dmin < keepout_um:
                    continue
            ref = comp << hole
            ref.move((float(x), float(y_mid)))
