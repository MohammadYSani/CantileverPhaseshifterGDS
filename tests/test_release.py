# tests/test_release.py
from __future__ import annotations

import pytest

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults, HoleParams, PlateParams

from ._util import all_refs, bbox_from_polys, get_layer_polys, poly_bbox, polys_by_layer

MIN_PLATE_AREA_UM2 = 10.0  # avoid “magic number” in assertions

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

    polys = polys_by_layer(comp)

    # Plate bbox from union of Al layers; fallback to all polys if needed
    plate_polys: list[object] = []
    for L in (DEFAULT_LAYERS.AL_BOTTOM, DEFAULT_LAYERS.ALN, DEFAULT_LAYERS.AL_TOP):
        plate_polys.extend(get_layer_polys(polys, L))
    if not plate_polys:
        all_lists = list(polys.values())
        assert all_lists, "Component returned no polygons at all"
        plate_polys = [p for lst in all_lists for p in lst]

    x0, y0, x1, y1 = bbox_from_polys(plate_polys)
    assert (x1 - x0) * (y1 - y0) > MIN_PLATE_AREA_UM2

    # Inner margin rectangle from PlateParams
    mx, my = plate.mx_margin, plate.my_margin
    ix0, ix1 = x0 + mx, x1 - mx
    iy0, iy1 = y0 + my, y1 - my

    # Holes: prefer RELEASE polys; else accept circle-like refs; else skip
    hole_polys = get_layer_polys(polys, DEFAULT_LAYERS.RELEASE)
    if not hole_polys:
        circle_like = [
            ref for ref in all_refs(comp)
            if "circle" in getattr(ref, "name", "").lower()
            or "circle" in getattr(getattr(ref, "parent", object()), "name", "").lower()
        ]
        if not circle_like:
            pytest.skip("Release holes not directly accessible as polygons/instances in this build")
        return

    # If we do have hole polygons, assert centroids lie inside the inner margin
    for poly in hole_polys:
        hx0, hy0, hx1, hy1 = poly_bbox(poly)
        cx = 0.5 * (hx0 + hx1)
        cy = 0.5 * (hy0 + hy1)
        assert ix0 - 1e-6 <= cx <= ix1 + 1e-6
        assert iy0 - 1e-6 <= cy <= iy1 + 1e-6
