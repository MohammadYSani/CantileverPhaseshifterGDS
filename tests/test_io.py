# tests/test_io.py
from __future__ import annotations

import pathlib
import tempfile

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import SerpentineParams


def test_write_gds(tmp_path: pathlib.Path | None = None) -> None:
    tmp = tmp_path or pathlib.Path(tempfile.mkdtemp())

    sp = SerpentineParams(
        n_loops=1,
        straight_um=100,
        bend_radius_um=20,
        width_um=0.4,
        pitch_um=40,
    )

    comp, meta = build_serpentine_multilayer_cell(sp, DEFAULT_LAYERS)

    out = tmp / "t.gds"
    write_gds_with_meta(comp, meta, str(out))

    assert out.exists() and out.stat().st_size > 0
