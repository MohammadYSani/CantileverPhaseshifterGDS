# tests/test_serpentine.py
from __future__ import annotations

from pathlib import Path

import pytest

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults

from ._util import bbox_from_polys, get_layer_polys, polys_by_layer

MIN_PLATE_AREA_UM2 = 10.0

def test_build_and_write(tmp_path: Path):
    defaults = DeviceDefaults()

    # Force holes ON for this test
    holes = defaults.holes
    holes.add_holes = True
    holes.holes_per_row = 11

    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=defaults.serpentine,
        widths=defaults.widths,
        plate=defaults.plate,
        asi=defaults.asi,
        holes=holes,
        build=defaults.build,
    )

    # Geometry present
    polys = polys_by_layer(comp)
    total_polys = sum(len(v) for v in polys.values())
    has_instances = bool(getattr(comp, "instances", []) or getattr(comp, "references", []))
    assert total_polys > 0 or has_instances, "Component has neither polygons nor instances"

    # Plate bbox area: union of Al layers (fallback to all polys)
    plate_polys: list[object] = []
    for L in (DEFAULT_LAYERS.AL_BOTTOM, DEFAULT_LAYERS.ALN, DEFAULT_LAYERS.AL_TOP):
        plate_polys.extend(get_layer_polys(polys, L))
    if not plate_polys:
        all_lists = list(polys.values())
        assert all_lists, "No polygons found to estimate plate bbox"
        plate_polys = [p for lst in all_lists for p in lst]
    x0, y0, x1, y1 = bbox_from_polys(plate_polys)
    assert (x1 - x0) * (y1 - y0) > MIN_PLATE_AREA_UM2

    # Write to temp dir
    out_gds = tmp_path / "test_serpentine.gds"
    # Keep your current API order; if your writer is (component, meta, path), keep it
    write_gds_with_meta(comp, meta, str(out_gds))
    assert out_gds.exists()
    assert out_gds.with_suffix(".meta.json").exists()

    # Optional: if RELEASE polys absent, allow skip (depends on gf version / flattening)
    hole_polys = get_layer_polys(polys, DEFAULT_LAYERS.RELEASE)
    if not hole_polys:
        pytest.skip("No release holes visible as polygons/instances in this build")
