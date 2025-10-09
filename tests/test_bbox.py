# tests/test_bbox.py
import math

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import SerpentineParams

TOL = 1e-2  # µm tolerance
def _bbox(c):
    (x0, y0), (x1, y1) = c.bbox  # gdsfactory bbox in microns
    return x1 - x0, y1 - y0

def test_design1_bbox_close():
    sp = SerpentineParams(n_loops=6, straight_um=300, bend_radius_um=40,
                          width_um=0.4, pitch_um=55, overhang_um=300)
    C = build_serpentine_multilayer_cell(sp, DEFAULT_LAYERS)
    w, h = _bbox(C)
    assert math.isclose(w, 350.0, rel_tol=0, abs_tol=TOL)
    assert math.isclose(h, 325.0, rel_tol=0, abs_tol=TOL)
