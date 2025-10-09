# tests/test_layers.py
from __future__ import annotations

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import SerpentineParams
from tests._util import polys_by_layer


def test_layers_present() -> None:
    sp = SerpentineParams(
        n_loops=2,
        straight_um=150,
        bend_radius_um=25,
        width_um=0.4,
        pitch_um=45,
    )

    comp, _ = build_serpentine_multilayer_cell(sp, DEFAULT_LAYERS)

    # Version-robust way to get the set of layer keys
    layer_map = polys_by_layer(comp)
    layers = set(layer_map)

    expect = {DEFAULT_LAYERS.WG, DEFAULT_LAYERS.ALN, DEFAULT_LAYERS.AL}
    assert expect.issubset(layers)
