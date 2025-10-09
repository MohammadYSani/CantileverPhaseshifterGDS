# tests/_util.py
from __future__ import annotations

from collections.abc import Iterable

import gdsfactory as gf
import numpy as np

# ---- small constants to avoid "magic numbers" ----
_POLY_MIN_COLS = 2  # x,y at least

_POLY_NDIM_EXPECTED = 2   # expected 2D (x, y)

def polys_by_layer(comp: gf.Component) -> dict[object, list[object]]:
    """Return polygons grouped by layer across gf versions; flatten if empty."""
    def _get(c: gf.Component) -> dict[object, list[object]]:
        try:
            return c.get_polygons(by_spec=True)        # older gdsfactory/phidl
        except TypeError:
            return c.get_polygons()                    # newer gdsfactory/kfactory

    polys = _get(comp)
    if sum(len(v) for v in polys.values()) > 0:
        return polys

    tmp = gf.Component("tmp_flat_for_tests")
    _ = tmp << comp
    tmp.flatten()
    return _get(tmp)

def all_refs(comp: gf.Component) -> list[object]:
    """Return references/instances across gf versions."""
    out: list[object] = []
    r1 = getattr(comp, "references", [])
    r2 = getattr(comp, "instances", [])
    if r1:
        out.extend(r1)
    if r2:
        out.extend(r2)
    return out

def get_layer_polys(polys: dict[object, list[object]], layer_tuple: tuple[int, int]) -> list[object]:
    """Fetch polygons whether dict is keyed by (layer, datatype) or just layer."""
    L, D = layer_tuple
    if (L, D) in polys:
        return polys[(L, D)]
    if L in polys:
        return polys[L]
    return []

# ---- bbox helpers, split to keep complexity low ----
def _numpy_bbox(poly: object) -> tuple[float, float, float, float] | None:
    try:
        xy = np.asarray(poly, dtype=float)
        if xy.ndim == _POLY_NDIM_EXPECTED and xy.shape[1] >= _POLY_MIN_COLS:
            x0, y0 = np.min(xy[:, :2], axis=0)
            x1, y1 = np.max(xy[:, :2], axis=0)
            return float(x0), float(y0), float(x1), float(y1)
    except Exception:
        pass
    return None

def _klayout_bbox(poly: object) -> tuple[float, float, float, float] | None:
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
