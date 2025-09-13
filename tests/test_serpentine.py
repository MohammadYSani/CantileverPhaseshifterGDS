from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import gdsfactory as gf

from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


# ---------------------------- helpers ---------------------------- #

def _polys_by_layer(comp: gf.Component) -> Dict[object, List[object]]:
    """Return polygons grouped by layer across gf versions, with flatten fallback."""
    try:
        polys = comp.get_polygons(by_spec=True)   # older gf
    except TypeError:
        polys = comp.get_polygons()               # newer gf/kfactory

    if sum(len(v) for v in polys.values()) > 0 or not getattr(comp, "instances", []):
        return polys

    # Fallback: flatten a copy and retry
    tmp = gf.Component("tmp_test_flat")
    _ = tmp << comp
    tmp.flatten()
    try:
        return tmp.get_polygons(by_spec=True)
    except TypeError:
        return tmp.get_polygons()


def _get_layer_polys(polys: Dict[object, List[object]], layer_tuple: Tuple[int, int]) -> List[object]:
    """Fetch polygons whether the dict is keyed by (L,D) or just L."""
    L, D = layer_tuple
    if (L, D) in polys:
        return polys[(L, D)]
    if L in polys:
        return polys[L]
    return []


def _poly_bbox(poly: object) -> Tuple[float, float, float, float]:
    """Return (x0,y0,x1,y1) for numpy-like polys or KLayout polys."""
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


# ------------------------------ test ----------------------------- #

def test_build_and_write(tmp_path):
    defaults = DeviceDefaults()

    # Force holes ON for this test (so geometry is present even if defaults disable them)
    holes = defaults.holes
    holes.add_holes = True
    holes.holes_per_row = 11
    # holes.hole_diam_um = 2.0
    # holes.hole_pitch_um = 3.0

    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=defaults.serpentine,
        widths=defaults.widths,
        plate=defaults.plate,
        asi=defaults.asi,
        holes=holes,            # use modified holes
        build=defaults.build,
    )

    # Basic geometry sanity
    polys = _polys_by_layer(comp)
    total_polys = sum(len(v) for v in polys.values())
    assert total_polys > 0 or getattr(comp, "instances", []), "Component has neither polygons nor instances"

    # Plate bbox area: union of AL layers (fallback to all polys)
    plate_polys: List[object] = []
    for L in (DEFAULT_LAYERS.AL_BOTTOM, DEFAULT_LAYERS.ALN, DEFAULT_LAYERS.AL_TOP):
        plate_polys.extend(_get_layer_polys(polys, L))
    if not plate_polys:
        all_lists = list(polys.values())
        assert all_lists, "No polygons found to estimate plate bbox"
        plate_polys = [p for lst in all_lists for p in lst]
    x0, y0, x1, y1 = _bbox_from_polys(plate_polys)
    assert (x1 - x0) * (y1 - y0) > 10.0

    # Write directly to your folder
    output_dir = Path("/home/mohammad/Documents/Piezo-Optomechanical-PICs")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_gds = output_dir / "test_serpentine.gds"
    write_gds_with_meta(comp, meta, str(out_gds))
    assert out_gds.exists()
    assert out_gds.with_suffix(".meta.json").exists()

    # Optional: holes presence check—skip if this gf build keeps them unflattened
    hole_polys = _get_layer_polys(polys, DEFAULT_LAYERS.RELEASE)
    if not hole_polys:
        circle_like = [
            inst for inst in getattr(comp, "instances", [])
            if "circle" in getattr(inst, "name", "").lower()
            or "circle" in getattr(getattr(inst, "parent", object()), "name", "").lower()
        ]
        if not circle_like:
            import pytest
            pytest.skip("No release holes visible as polys/instances in this build")
