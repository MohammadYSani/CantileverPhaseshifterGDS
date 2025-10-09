# src/piezo_pic/cells/stack.py
from __future__ import annotations

import gdsfactory as gf
import numpy as np

from ..tech.layers import LayerMap
from ..tech.params import ASiParams, PlateParams
from ..utils.geometry import bbox_xyxy

_MIN_SIZE = 1e-6  # avoid zero-size rectangles


def build_plate_and_asi_unrotated(
    D: gf.Component,
    path_points_um: np.ndarray,        # centerline points (unrotated)
    plate: PlateParams,
    asi: ASiParams,
    layers: LayerMap,
) -> tuple[gf.ComponentReference, gf.ComponentReference | None, list[gf.ComponentReference]]:
    """
    Create the trilayer plate rectangles (Al bottom / AlN / Al top) and the
    optional a-Si rectangle in the *final* (non-rotated) frame.

    Returns
    -------
    r_plate_top :
        Top Al reference (representative plate ref).
    r_asi :
        a-Si rectangle reference (rough placement) or None.
    r_plate_all :
        [r_al_bottom, r_aln, r_al_top] — useful for union bbox or later ops.
    """
    pts = np.asarray(path_points_um, dtype=float)
    if pts.size == 0:
        raise ValueError("path_points_um is empty; cannot size plate.")

    xmin, xmax = float(np.min(pts[:, 0])), float(np.max(pts[:, 0]))
    ymin, ymax = float(np.min(pts[:, 1])), float(np.max(pts[:, 1]))
    xspan = max(_MIN_SIZE, xmax - xmin)
    yspan = max(_MIN_SIZE, ymax - ymin)
    ycenter = 0.5 * (ymin + ymax)

    # Plate size & position
    if plate.mstack_rect_length_um is None:
        rect_l = float(xspan + 2.0 * float(plate.mx_margin))
        rect_left_x = float(xmin - float(plate.mx_margin))
    else:
        rect_l = float(plate.mstack_rect_length_um)
        rect_left_x = float(xmin)

    # Ensure the plate at least covers the serpentine + margins in Y
    rect_w = float(max(float(plate.mstack_rect_width_um), yspan + 2.0 * float(plate.my_margin)))

    rect_l = max(_MIN_SIZE, rect_l)
    rect_w = max(_MIN_SIZE, rect_w)

    # --- Build identical rectangles on AL_BOTTOM, ALN, AL_TOP ---
    r_plate_all: list[gf.ComponentReference] = []
    for L in (layers.AL_BOTTOM, layers.ALN, layers.AL_TOP):
        rect = gf.components.rectangle(size=(rect_l, rect_w), layer=L)
        r = D << rect
        r.move((
            rect_left_x + float(plate.mstack_rect_dx_um),
            (ycenter - rect_w / 2.0) + float(plate.mstack_rect_dy_um),
        ))
        r_plate_all.append(r)

    # Representative plate ref: use the top Al layer
    r_plate_top = r_plate_all[-1]  # AL_TOP

    # --- a-Si overhang (rough placement; no rotation) ---
    r_asi: gf.ComponentReference | None = None
    if asi.add_asi:
        # Y-size of a-Si is clamped to the plate height so it never sticks out
        asi_w = float(min(float(asi.asi_rect_width_um), rect_w))
        # X-length extends to the left by asi_overhang_left_um (≥0)
        asi_len = float(rect_l + max(0.0, float(asi.asi_overhang_left_um)))
        a_si = gf.components.rectangle(
            size=(max(_MIN_SIZE, asi_len), max(_MIN_SIZE, asi_w)),
            layer=layers.ASI,
        )
        r_asi = D << a_si
        r_asi.move((rect_left_x, ycenter - asi_w / 2.0))

    return r_plate_top, r_asi, r_plate_all


def align_asi_to_plate_left(
    r_plate: gf.ComponentReference,
    r_asi: gf.ComponentReference | None,
    asi: ASiParams,
) -> None:
    """
    Snap a-Si left edge to plate left edge (no rotation used).
    Aligns top edges and applies overhang + fine dx/dy from ASiParams.
    """
    if (r_asi is None) or (not asi.add_asi):
        return

    px0, py0, px1, py1 = bbox_xyxy(r_plate)
    ax0, ay0, ax1, ay1 = bbox_xyxy(r_asi)

    dx = (px0 - ax0) - max(0.0, float(asi.asi_overhang_left_um)) + float(asi.asi_rect_dx_um)
    dy = (py1 - ay1) + float(asi.asi_rect_dy_um)  # align TOP edges
    r_asi.move((float(dx), float(dy)))


# --- optional backward-compatibility shim ---
def align_asi_to_plate_left_after_rotation(
    r_plate: gf.ComponentReference,
    r_asi: gf.ComponentReference | None,
    asi: ASiParams,
) -> None:
    """Deprecated alias for align_asi_to_plate_left (rotation no longer used)."""
    align_asi_to_plate_left(r_plate, r_asi, asi)
