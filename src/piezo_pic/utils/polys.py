# src/piezo_pic/utils/polys.py
"""
Polygon and layer utilities for gdsfactory components.

These helpers make the code robust against API differences
between gdsfactory versions (Phidl vs kfactory style).
"""

from __future__ import annotations

from collections.abc import Iterable

import gdsfactory as gf
import numpy as np

# constants to avoid “magic numbers”
_POLY_MIN_COLS = 2        # x, y at least
_POLY_NDIM_EXPECTED = 2   # 2D polygons


def polys_by_layer(comp: gf.Component) -> dict[object, list[object]]:
    """Return polygons grouped by layer across gdsfactory versions.

    Falls back to flattening a temporary copy if the component
    stores geometry only in references.
    """
    def _get(c: gf.Component) -> dict[object, list[object]]:
        try:
            return c.get_polygons(by_spec=True)        # older gdsfactory/phidl
        except TypeError:
            return c.get_polygons()                    # newer gdsfactory/kfactory

    polys = _get(comp)
    if sum(len(v) for v in polys.values()) > 0:
        return polys

    # Fallback: flatten once
    tmp = gf.Component("tmp_flat_for_utils")
    _ = tmp << comp
    tmp.flatten()
    return _get(tmp)


def all_refs(comp: gf.Component) -> list[object]:
    """Return all sub-component references, independent of API."""
    out: list[object] = []
    for attr in ("references", "instances"):
        val = getattr(comp, attr, None)
        if val:
            out.extend(val)
    return out


def get_layer_polys(polys: dict[object, list[object]], layer_tuple: tuple[int, int]) -> list[object]:
    """Fetch polygons whether the dict is keyed by (layer, datatype) or just layer."""
    L, D = layer_tuple
    if (L, D) in polys:
        return polys[(L, D)]
    if L in polys:
        return polys[L]
    return []


# ---- bbox helpers ----
def _numpy_bbox(poly: object) -> tuple[float, float, float, float] | None:
    """Try to extract bbox from numpy-like polygon array."""
    try:
        xy = np.asarray(poly, dtype=float)
        if xy.ndim == _POLY_NDIM_EXPECTED and xy.shape[1] >= _POLY_MIN_COLS:
            x0, y0 = np.min(xy[:, :2], axis=0)
            x1, y1 = np.max(xy[:, :2], axis=0)
            return float(x0), float(y0), float(x1), float(y1)
    except Exception:
        return None
    return None


def _klayout_bbox(poly: object) -> tuple[float, float, float, float] | None:
    """Try bbox() or .bbox attribute (KLayout style)."""
    box_attr = getattr(poly, "bbox", None)
    if box_attr is None:
        return None
    try:
        b = box_attr() if callable(box_attr) else box_attr
        if hasattr(b, "left"):
            return float(b.left), float(b.bottom), float(b.right), float(b.top)
        if hasattr(b, "p1") and hasattr(b, "p2"):
            return float(b.p1.x), float(b.p1.y), float(b.p2.x), float(b.p2.y)
    except Exception:
        return None
    return None


def _iter_points_bbox(poly: object) -> tuple[float, float, float, float] | None:
    """Try each_point() / each_point_hull() iterator."""
    for itname in ("each_point", "each_point_hull"):
        it = getattr(poly, itname, None)
        if not callable(it):
            continue
        pts: list[tuple[float, float]] = []
        try:
            for p in it():  # type: ignore[func-returns-value]
                pts.append((float(p.x), float(p.y)))
        except Exception:
            continue
        if pts:
            xy = np.asarray(pts, dtype=float)
            x0, y0 = xy.min(axis=0)
            x1, y1 = xy.max(axis=0)
            return float(x0), float(y0), float(x1), float(y1)
    return None


def poly_bbox(poly: object) -> tuple[float, float, float, float]:
    """Return (x0, y0, x1, y1) for numpy-like or KLayout-style polygon objects."""
    for fn in (_numpy_bbox, _klayout_bbox, _iter_points_bbox):
        out = fn(poly)
        if out is not None:
            return out
    raise TypeError("Unsupported polygon type for bbox")


def bbox_from_polys(polys: Iterable[object]) -> tuple[float, float, float, float]:
    """Compute union bbox of all polygons."""
    xs0: list[float] = []
    ys0: list[float] = []
    xs1: list[float] = []
    ys1: list[float] = []
    for p in polys:
        x0, y0, x1, y1 = poly_bbox(p)
        xs0.append(x0)
        ys0.append(y0)
        xs1.append(x1)
        ys1.append(y1)
    return min(xs0), min(ys0), max(xs1), max(ys1)
