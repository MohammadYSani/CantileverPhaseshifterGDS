# src/piezo_pic/utils/geometry.py
from __future__ import annotations

from collections.abc import Iterable
from math import cos, radians, sin

import numpy as np

# ---- Module constants (avoid "magic numbers") ----
_POLY_MIN_COLS = 2          # minimum columns expected for (x, y) point arrays
_BBOX_TUPLE_LEN = 4         # length of plain bbox tuples: (x0, y0, x1, y1)


# ---- Path helpers (support old/new gdsfactory Path) ----
def path_length_um(P) -> float:
    """Return length of a gdsfactory Path in microns, with fallbacks."""
    if hasattr(P, "length"):
        try:
            return float(P.length())
        except Exception:
            pass

    pts = np.asarray(getattr(P, "points", []), dtype=float)
    if len(pts) < _POLY_MIN_COLS:
        return 0.0

    segs = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
    return float(segs.sum())


def sample_points_um(P, s_vals_um: Iterable[float]) -> np.ndarray:
    """Sample centerline points along a Path at given arclength positions (µm)."""
    s_vals_um = np.asarray(s_vals_um, dtype=float)

    if hasattr(P, "sample"):
        try:
            return P.sample(s_vals_um)
        except Exception:
            pass

    pts = np.asarray(getattr(P, "points", []), dtype=float)
    if len(pts) == 0:
        return np.zeros((0, 2))
    if len(pts) == 1:
        return np.repeat(pts, len(s_vals_um), axis=0)

    segs = np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1))
    s_cum = np.concatenate([[0.0], np.cumsum(segs)])
    x = np.interp(s_vals_um, s_cum, pts[:, 0])
    y = np.interp(s_vals_um, s_cum, pts[:, 1])
    return np.column_stack([x, y])


def rotate_xy(xy: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotate Nx2 array by angle_deg about the origin (0,0)."""
    if angle_deg % 360 == 0:
        return xy.copy()
    t = radians(angle_deg)
    c, s = cos(t), sin(t)
    xr = c * xy[:, 0] - s * xy[:, 1]
    yr = s * xy[:, 0] + c * xy[:, 1]
    return np.column_stack([xr, yr])


# ---- BBox across gdsfactory versions ----
def bbox_xyxy(ref) -> tuple[float, float, float, float]:
    """
    Return (xmin, ymin, xmax, ymax) for a ComponentReference or Component,
    compatible with multiple gdsfactory versions.
    """
    b = ref.bbox() if callable(getattr(ref, "bbox", None)) else ref.bbox

    # Common structured bbox shapes
    if all(hasattr(b, a) for a in ("xmin", "ymin", "xmax", "ymax")):
        return float(b.xmin), float(b.ymin), float(b.xmax), float(b.ymax)
    if all(hasattr(b, a) for a in ("left", "bottom", "right", "top")):
        return float(b.left), float(b.bottom), float(b.right), float(b.top)
    if all(hasattr(b, a) for a in ("p1", "p2")) and \
       all(hasattr(b.p1, a) for a in ("x", "y")) and \
       all(hasattr(b.p2, a) for a in ("x", "y")):
        return float(b.p1.x), float(b.p1.y), float(b.p2.x), float(b.p2.y)

    # Plain tuple/list bbox
    try:
        if len(b) == _BBOX_TUPLE_LEN and all(isinstance(v, (int, float)) for v in b):
            x0, y0, x1, y1 = b
            return float(x0), float(y0), float(x1), float(y1)
    except TypeError:
        # Not an iterable; fall through to pair-of-pairs below
        pass

    # Pair of coordinate pairs: ((x0, y0), (x1, y1))
    (x0, y0), (x1, y1) = b
    return float(x0), float(y0), float(x1), float(y1)


# ---- Geometry utility: min distance from point to polyline ----
def min_dist_point_polyline(px: float, py: float, poly_xy: np.ndarray) -> float:
    """Minimum Euclidean distance from (px,py) to polyline defined by Nx2 vertices."""
    v = poly_xy[:-1]
    w = poly_xy[1:]
    dv = w - v
    pv = np.asarray([px, py]) - v
    seg_len2 = (dv[:, 0] ** 2 + dv[:, 1] ** 2) + 1e-18
    t = (pv[:, 0] * dv[:, 0] + pv[:, 1] * dv[:, 1]) / seg_len2
    t = np.clip(t, 0.0, 1.0)
    proj = v + (t[:, None] * dv)
    d2 = (proj[:, 0] - px) ** 2 + (proj[:, 1] - py) ** 2
    return float(np.sqrt(d2.min()))
