from __future__ import annotations

from typing import Dict, Any, Tuple, List, Optional
from uuid import uuid4

import numpy as np
import gdsfactory as gf

from ..geometry.serpentine import serpentine_path_um
from ..utils.geometry import bbox_xyxy, path_length_um, sample_points_um
from ..tech.layers import LayerMap
from ..tech.params import (
    SerpentineParams,
    WaveguideWidths,
    PlateParams,
    ASiParams,
    HoleParams,
    BuildParams,
)
from ..features.release import add_release_rows_at_seams_final_frame
from .stack import (
    build_plate_and_asi_unrotated,
    align_asi_to_plate_left_after_rotation,
)


def _extrude_layer(P, width_um: float, layer) -> gf.ComponentReference:
    """Extrudes a path with a simple strip cross-section on the given layer."""
    xs = gf.cross_section.strip(width=width_um, layer=layer)
    return gf.path.extrude(P, cross_section=xs)


def _union_bbox_of_refs(refs: List[gf.ComponentReference]) -> Tuple[float, float, float, float]:
    """Union bbox of multiple references."""
    xmins: List[float] = []
    ymins: List[float] = []
    xmaxs: List[float] = []
    ymaxs: List[float] = []
    for r in refs:
        x0, y0, x1, y1 = bbox_xyxy(r)
        xmins.append(x0); ymins.append(y0); xmaxs.append(x1); ymaxs.append(y1)
    return min(xmins), min(ymins), max(xmaxs), max(ymaxs)


def build_serpentine_multilayer_cell(
    *,
    layers: LayerMap,
    serp: SerpentineParams,
    widths: WaveguideWidths,
    plate: PlateParams,
    asi: ASiParams,
    holes: HoleParams,
    build: BuildParams,
) -> Tuple[gf.Component, Dict[str, Any]]:
    """
    Compose the full multilayer device as a gdsfactory.Component (no file I/O).
    """
    # 1) Serpentine centerline (µm)
    P = serpentine_path_um(
        iterations=serp.iterations,
        radius_um=serp.radius_um,
        length_um=serp.length_um,
        npts_per_bend=serp.npts_per_bend,
    )

    # 2) Top-level component
    D = gf.Component(f"serpentine_multilayer_{uuid4().hex[:8]}")

    # 3) Oxide + SiN (UNROTATED frame)
    if widths.add_oxide:
        D << _extrude_layer(P, width_um=widths.width_oxide_um, layer=layers.OXIDE)
    D << _extrude_layer(P, width_um=widths.width_sin_um, layer=layers.SIN)

    # 4) Plate + a-Si (UNROTATED frame)
    pts = np.asarray(P.points)
    r_plate_top, r_asi, r_plate_all = build_plate_and_asi_unrotated(
        D=D, path_points_um=pts, plate=plate, asi=asi, layers=layers
    )

    # Normalize list of plate refs
    if not isinstance(r_plate_all, list) or len(r_plate_all) == 0:
        r_plate_all = [r_plate_top]

    # 5) Align a-Si to plate (still unrotated)
    align_asi_to_plate_left_after_rotation(r_plate_top, r_asi, asi)

    # --- Compute bboxes now (used both for holes and meta) ---
    bxmin, bymin, bxmax, bymax = _union_bbox_of_refs(r_plate_all)
    px0, py0, px1, py1 = bxmin, bymin, bxmax, bymax
    rect_l = float(px1 - px0)
    rect_w = float(py1 - py0)

    # Optional a-Si bbox (to restrict holes to overhang region in Y and/or X)
    asi_y_range: Optional[Tuple[float, float]] = None
    asi_x_range: Optional[Tuple[float, float]] = None
    if r_asi is not None:
        ax0, ay0, ax1, ay1 = bbox_xyxy(r_asi)
        # Intersect with plate inner margins when placing holes
        asi_y_range = (ay0, ay1)
        asi_x_range = (ax0, ax1)

    # 6) Release holes (UNROTATED final frame)
    if holes.add_holes:
        # Sample the centerline robustly
        s_vals = np.linspace(0.0, path_length_um(P), 4000)
        pts_final = sample_points_um(P, s_vals)  # final == unrotated

        # Build clipping windows:
        x_range = asi_x_range  # if a-Si shorter in X, this limits holes in clamp region
        y_range = asi_y_range  # limits holes to the a-Si overhang span in Y

        add_release_rows_at_seams_final_frame(
            comp=D,
            P=P,
            plate_bbox_xyxy=(bxmin, bymin, bxmax, bymax),
            rotate_deg=0.0,
            layers=layers,
            holes=holes,
            widths=widths,
            sample_N=4000,
            straight_tol=0.06,
            bend_trim_um=2.0,
            mx_margin=plate.mx_margin,
            my_margin=plate.my_margin,
            pts_final=pts_final,
            x_range=x_range,     # NEW
            y_range=y_range,     # NEW
        )

    # 7) Metadata for sidecar JSON
    meta: Dict[str, Any] = {
        "description": (
            "Serpentine SiN with oxide overclad, Al/AlN/Al trilayer plate, "
            "a-Si overhang, and (optional) release holes."
        ),
        "layers": {
            "SiN": {
                "gds_layer": layers.SIN[0],
                "datatype": layers.SIN[1],
                "width_um": widths.width_sin_um,
            },
            "Oxide": {
                "gds_layer": layers.OXIDE[0],
                "datatype": layers.OXIDE[1],
                "width_um": widths.width_oxide_um,
                "enabled": widths.add_oxide,
            },
            "aSi_overhang": {
                "gds_layer": layers.ASI[0],
                "datatype": layers.ASI[1],
                "enabled": asi.add_asi,
            },
            "Al_bottom_plate": {
                "gds_layer": layers.AL_BOTTOM[0],
                "datatype": layers.AL_BOTTOM[1],
                "size_um": (rect_l, rect_w),
                "mx_margin": plate.mx_margin,
                "my_margin": plate.my_margin,
            },
            "AlN_plate": {
                "gds_layer": layers.ALN[0],
                "datatype": layers.ALN[1],
                "size_um": (rect_l, rect_w),
                "mx_margin": plate.mx_margin,
                "my_margin": plate.my_margin,
            },
            "Al_top_plate": {
                "gds_layer": layers.AL_TOP[0],
                "datatype": layers.AL_TOP[1],
                "size_um": (rect_l, rect_w),
                "mx_margin": plate.mx_margin,
                "my_margin": plate.my_margin,
            },
            "ReleaseHoles": {
                "gds_layer": layers.RELEASE[0],
                "datatype": layers.RELEASE[1],
                "hole_diam_um": holes.hole_diam_um,
                "pitch_x_um": holes.hole_pitch_um,
                "holes_per_row": holes.holes_per_row,
                "enabled": holes.add_holes,
            },
        },
        "build": {"rotate_deg": 0.0},
        "serpentine": serp.model_dump(),
    }

    return D, meta
