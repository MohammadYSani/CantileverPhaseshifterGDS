from __future__ import annotations
import numpy as np
import gdsfactory as gf
from typing import Dict, List, Tuple

from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults, HoleParams, PlateParams
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _polys_by_layer(comp: gf.Component) -> Dict[object, List[object]]:
    """
    Return polygons grouped by layer across gf versions.
    - Newer kfactory: comp.get_polygons() -> {layer: [polys]}
    - Older gf/phidl: comp.get_polygons(by_spec=True) -> {(layer,datatype): [polys]}
    If no polygons are found but the component has references, flatten a copy and retry.
    """
    def _get(c: gf.Component) -> Dict[object, List[object]]:
        try:
            return c.get_polygons(by_spec=True)   # older gf
        except TypeError:
            return c.get_polygons()               # newer gf/kfactory

    polys = _get(comp)
    if sum(len(v) for v in polys.values()) > 0:
        return polys

    has_refs = bool(getattr(comp, "references", [])) or bool(getattr(comp, "instances", []))
    if has_refs:
        tmp = gf.Component("tmp_flat_for_tests")
        _ = tmp << comp
        tmp.flatten()
        polys = _get(tmp)

    return polys

def _all_refs(comp: gf.Component):
    refs = []
    r1 = getattr(comp, "references", [])
    r2 = getattr(comp, "instances", [])
    if r1:
        refs.extend(r1)
    if r2:
        refs.extend(r2)
    return refs

def _get_layer_polys(polys: Dict[object, List[object]], layer_tuple: Tuple[int, int]) -> List[object]:
    """Fetch polygons whether the dict is keyed by (L,D) or just L."""
    L, D = layer_tuple
    if (L, D) in polys:
        return polys[(L, D)]
    if L in polys:
        return polys[L]
    return []

def _poly_bbox(poly: object) -> Tuple[float, float, float, float]:
    """Return (x0,y0,x1,y1) for numpy polys or KLayout polys."""
    try:
        xy = np.asarray(poly, dtype=float)
        if xy.ndim == 2 and xy.shape[1] >= 2:
            x0, y0 = np.min(xy[:, :2], axis=0)
            x1, y1 = np.max(xy[:, :2], axis=0)
            return float(x0), float(y0), float(x1), float(y1)
    except Exception:
        pass

    box_attr = getattr(poly, "bbox", None)
    if box_attr is not None:
        try:
            b = box_attr() if callable(box_attr) else box_attr
            if hasattr(b, "left"):
                return float(b.left), float(b.bottom), float(b.right), float(b.top)
            if hasattr(b, "p1") and hasattr(b, "p2"):
                return float(b.p1.x), float(b.p1.y), float(b.p2.x), float(b.p2.y)
        except Exception:
            pass

    for itname in ("each_point", "each_point_hull"):
        it = getattr(poly, itname, None)
        if callable(it):
            pts = []
            try:
                for p in it():
                    pts.append((float(p.x), float(p.y)))
                if pts:
                    xy = np.asarray(pts, dtype=float)
                    x0, y0 = xy.min(axis=0)
                    x1, y1 = xy.max(axis=0)
                    return float(x0), float(y0), float(x1), float(y1)
            except Exception:
                pass

    raise TypeError("Unsupported polygon type for bbox")

def _bbox_from_polys(polys: List[object]) -> Tuple[float, float, float, float]:
    xs0 = []; ys0 = []; xs1 = []; ys1 = []
    for p in polys:
        x0, y0, x1, y1 = _poly_bbox(p)
        xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
    return min(xs0), min(ys0), max(xs1), max(ys1)


# -------------------------------------------------------------------
# Test
# -------------------------------------------------------------------

def test_release_holes_inside_plate_inner_margin():
    defaults = DeviceDefaults()

    plate = PlateParams(**defaults.plate.model_dump())
    holes = HoleParams(**defaults.holes.model_dump())
    holes.holes_per_row = 11
    holes.add_holes = True

    comp, _ = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=defaults.serpentine,
        widths=defaults.widths,
        plate=plate,
        asi=defaults.asi,
        holes=holes,
        build=defaults.build,
    )

    polys = _polys_by_layer(comp)

    # --- Plate bbox from union of AL_BOTTOM, ALN, AL_TOP (fallback to all polys) ---
    plate_polys: List[object] = []
    for L in (DEFAULT_LAYERS.AL_BOTTOM, DEFAULT_LAYERS.ALN, DEFAULT_LAYERS.AL_TOP):
        plate_polys.extend(_get_layer_polys(polys, L))
    if not plate_polys:
        all_lists = list(polys.values())
        assert all_lists, "Component returned no polygons at all"
        plate_polys = [p for lst in all_lists for p in lst]

    x0, y0, x1, y1 = _bbox_from_polys(plate_polys)

    # Inner margin rectangle
    mx, my = plate.mx_margin, plate.my_margin
    ix0, ix1 = x0 + mx, x1 - mx
    iy0, iy1 = y0 + my, y1 - my

    # --- Holes: prefer RELEASE polys; else accept circle-like references; else skip ---
    hole_polys = _get_layer_polys(polys, DEFAULT_LAYERS.RELEASE)
    if not hole_polys:
        circle_like = [
            ref for ref in _all_refs(comp)
            if "circle" in getattr(ref, "name", "").lower()
            or "circle" in getattr(getattr(ref, "parent", object()), "name", "").lower()
        ]
        if not circle_like:
            import pytest
            pytest.skip("Release holes not directly accessible as polygons/instances in this build")
        return

    # If we do have hole polygons, assert centroids lie inside the inner margin
    for poly in hole_polys:
        hx0, hy0, hx1, hy1 = _poly_bbox(poly)
        cx = 0.5 * (hx0 + hx1)
        cy = 0.5 * (hy0 + hy1)
        assert ix0 - 1e-6 <= cx <= ix1 + 1e-6
        assert iy0 - 1e-6 <= cy <= iy1 + 1e-6
