# src/piezo_pic/cells/stack.py
from __future__ import annotations
from typing import Optional, Tuple, List
import numpy as np
import gdsfactory as gf

from ..utils.geometry import bbox_xyxy
from ..tech.layers import LayerMap
from ..tech.params import PlateParams, ASiParams


def build_plate_and_asi_unrotated(
    D: gf.Component,
    path_points_um: np.ndarray,        # centerline points (unrotated)
    plate: PlateParams,
    asi: ASiParams,
    layers: LayerMap,
) -> Tuple[gf.ComponentReference, Optional[gf.ComponentReference], List[gf.ComponentReference]]:
    """
    Create the trilayer plate rectangles (Al bottom / AlN / Al top) and the
    optional a-Si overhang in the current (unrotated) frame.

    Returns
    -------
    r_plate_top : ComponentReference
        Representative plate reference (top Al).
    r_asi : Optional[ComponentReference]
        a-Si rectangle reference (rough placement) or None.
    r_plate_all : list[ComponentReference]
        [r_al_bottom, r_aln, r_al_top] for union bbox / downstream ops.
    """
    pts = np.asarray(path_points_um)
    if pts.size == 0:
        raise ValueError("path_points_um is empty; cannot size plate.")

    xmin, xmax = float(pts[:, 0].min()), float(pts[:, 0].max())
    ymin, ymax = float(pts[:, 1].min()), float(pts[:, 1].max())
    xspan = xmax - xmin
    yspan = ymax - ymin
    ycenter = 0.5 * (ymin + ymax)

    # Plate size & position
    # Note: parameter names keep "mstack_*" for backward-compatibility.
    if plate.mstack_rect_length_um is None:
        rect_l = xspan + 2 * plate.mx_margin
        rect_left_x = xmin - plate.mx_margin
    else:
        rect_l = plate.mstack_rect_length_um
        rect_left_x = xmin

    # Ensure the plate at least covers the serpentine + margins in Y
    rect_w = max(plate.mstack_rect_width_um, yspan + 2 * plate.my_margin)

    # --- Build identical rectangles on AL_BOTTOM, ALN, AL_TOP ---
    r_plate_all: List[gf.ComponentReference] = []
    for L in (layers.AL_BOTTOM, layers.ALN, layers.AL_TOP):
        rect = gf.components.rectangle(size=(rect_l, rect_w), layer=L)
        r = D << rect
        r.move((
            rect_left_x + plate.mstack_rect_dx_um,
            (ycenter - rect_w / 2) + plate.mstack_rect_dy_um,
        ))
        r_plate_all.append(r)

    # Representative plate ref: use the top Al layer
    r_plate_top = r_plate_all[-1]  # AL_TOP

    # --- a-Si overhang (rough placement; exact snap done by align_asi_to_plate_left_after_rotation) ---
    r_asi = None
    if asi.add_asi:
        # Y-size of a-Si is clamped to the plate height so it never sticks out
        asi_w = min(asi.asi_rect_width_um, rect_w)
        # X-length extends to the left by asi_overhang_left_um (>=0) when snapped
        asi_len = rect_l + max(0.0, asi.asi_overhang_left_um)
        aSi = gf.components.rectangle(size=(asi_len, asi_w), layer=layers.ASI)
        r_asi = D << aSi
        r_asi.move((rect_left_x, ycenter - asi_w / 2))

    return r_plate_top, r_asi, r_plate_all


def align_asi_to_plate_left_after_rotation(
    r_plate: gf.ComponentReference,
    r_asi: Optional[gf.ComponentReference],
    asi: ASiParams,
) -> None:
    """
    In the FINAL (rotated) frame, snap a-Si left edge to plate left edge,
    applying overhang and fine dx/dy from ASiParams.
    """
    if (r_asi is None) or (not asi.add_asi):
        return

    px0, py0, px1, py1 = bbox_xyxy(r_plate)
    ax0, ay0, ax1, ay1 = bbox_xyxy(r_asi)

    dx = (px0 - ax0) - max(0.0, asi.asi_overhang_left_um) + asi.asi_rect_dx_um
    # align TOP edges instead of centers
    dy = (py1 - ay1) + asi.asi_rect_dy_um

    r_asi.move((dx, dy))
