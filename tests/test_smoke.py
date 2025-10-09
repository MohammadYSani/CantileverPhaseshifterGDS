# tests/test_smoke.py
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import SerpentineParams


def test_build_smoke():
    sp = SerpentineParams(n_loops=3, straight_um=200, bend_radius_um=30,
                          width_um=0.4, pitch_um=50, overhang_um=100)
    C = build_serpentine_multilayer_cell(sp, DEFAULT_LAYERS)
    assert C is not None
    assert len(C.references) > 0
