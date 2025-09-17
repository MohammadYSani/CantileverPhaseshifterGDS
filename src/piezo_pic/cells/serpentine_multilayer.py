# src/piezo_pic/cells/serpentine_multilayer.py
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
    align_asi_to_plate_left_after_rotation,  # name kept for compatibility
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

    Returns
    -------
    (component, meta)
      component : gf.Component
          The assembled layout.
      meta : Dict[str, Any]
          Metadata suitable for a sidecar JSON.
    """
    # 1) Serpentine centerline (µm)
    P = serpentine_path_um(
        iterations=serp.iterations,
        radius_um=serp.radius_um,
        length_um=serp.length_um,
        npts_per_bend=serp.npts_per_bend,
    )

    # 2) Top-level component; unique-ish name to avoid KLayout name clashes
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

    # Backward-compatibility: normalize if helper returned a single ref
    if isinstance(r_plate_all, (type(None), gf.ComponentReference.__class__)) or not isinstance(r_plate_all, list):
        r_plate_all = [r_plate_top]

    # 5) Align a-Si to plate (still valid in unrotated frame)
    align_asi_to_plate_left_after_rotation(r_plate_top, r_asi, asi)

    # 6) Release holes (UNROTATED final frame)
    if holes.add_holes:
        # Plate bbox: union of all plate refs
        bxmin, bymin, bxmax, bymax = _union_bbox_of_refs(r_plate_all)

        # Sample the centerline robustly (works across gf versions)
        s_vals = np.linspace(0.0, path_length_um(P), 4000)
        pts_final = sample_points_um(P, s_vals)  # final == unrotated

        add_release_rows_at_seams_final_frame(
            comp=D,
            P=P,
            plate_bbox_xyxy=(bxmin, bymin, bxmax, bymax),
            rotate_deg=0.0,  # no global rotation
            layers=layers,
            holes=holes,
            widths=widths,
            sample_N=4000,
            straight_tol=0.06,
            bend_trim_um=2.0,
            mx_margin=plate.mx_margin,
            my_margin=plate.my_margin,
            pts_final=pts_final,
        )

    # 7) Metadata for sidecar JSON (dimensions in current unrotated frame)
    px0, py0, px1, py1 = _union_bbox_of_refs(r_plate_all)
    rect_l = float(px1 - px0)
    rect_w = float(py1 - py0)

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
                "overhang_left_um": asi.asi_overhang_left_um,
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
