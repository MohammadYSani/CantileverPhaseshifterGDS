# src/piezo_pic/cells/serpentine_multilayer.py
from __future__ import annotations

from typing import Any
from uuid import uuid4

import gdsfactory as gf
import numpy as np

from ..features.release import add_release_rows_at_seams_final_frame
from ..geometry.serpentine import serpentine_path_um
from ..tech.layers import LayerMap
from ..tech.params import (
    ASiParams,
    BuildParams,
    HoleParams,
    PlateParams,
    SerpentineParams,
    WaveguideWidths,
)
from ..utils.geometry import bbox_xyxy, path_length_um, sample_points_um
from .stack import (
    align_asi_to_plate_left,
    build_plate_and_asi_unrotated,
)


def _extrude_layer(P, width_um: float, layer) -> gf.ComponentReference:
    """Extrude a path with a simple strip cross-section on the given layer."""
    xs = gf.cross_section.strip(width=width_um, layer=layer)
    return gf.path.extrude(P, cross_section=xs)


def _union_bbox_of_refs(refs: list[gf.ComponentReference]) -> tuple[float, float, float, float]:
    """Union bbox of multiple references."""
    xmins: list[float] = []
    ymins: list[float] = []
    xmaxs: list[float] = []
    ymaxs: list[float] = []
    for r in refs:
        x0, y0, x1, y1 = bbox_xyxy(r)
        xmins.append(x0)
        ymins.append(y0)
        xmaxs.append(x1)
        ymaxs.append(y1)
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
) -> tuple[gf.Component, dict[str, Any]]:
    """
    Compose the full multilayer device as a gdsfactory.Component (no file I/O).
    Rotation is not used; the unrotated frame is the final frame.
    """
    # 1) Serpentine centerline (µm)
    P = serpentine_path_um(
        iterations=serp.iterations,
        radius_um=serp.radius_um,
        length_um=serp.length_um,
        npts_per_bend=serp.npts_per_bend,
        band_height_um=getattr(serp, "band_height_um", None),
        y_margin_um=getattr(serp, "y_margin_um", 0.0),
    )

    # 2) Top-level component
    D = gf.Component(f"serpentine_multilayer_{uuid4().hex[:8]}")

    # 3) Oxide + SiN (FINAL frame)
    r_oxide = None
    if widths.add_oxide:
        r_oxide = D << _extrude_layer(P, width_um=widths.width_oxide_um, layer=layers.OXIDE)
    r_sin = D << _extrude_layer(P, width_um=widths.width_sin_um, layer=layers.SIN)

    # Optional: shift core + cladding as a block by serp.y_offset_um
    if getattr(serp, "y_offset_um", 0.0) != 0.0:
        dy = float(serp.y_offset_um)
        if r_oxide is not None:
            r_oxide.movey(dy)
        r_sin.movey(dy)

    # 4) Plate + a-Si (FINAL frame)
    pts = np.asarray(P.points)
    r_plate_top, r_asi, r_plate_all = build_plate_and_asi_unrotated(
        D=D, path_points_um=pts, plate=plate, asi=asi, layers=layers
    )

    # Normalize list of plate refs
    if not isinstance(r_plate_all, list) or len(r_plate_all) == 0:
        r_plate_all = [r_plate_top]

    # 5) Align a-Si to plate (FINAL frame)
    align_asi_to_plate_left(r_plate_top, r_asi, asi)

    # --- Compute bboxes now (used both for holes and meta) ---
    bxmin, bymin, bxmax, bymax = _union_bbox_of_refs(r_plate_all)
    px0, py0, px1, py1 = bxmin, bymin, bxmax, bymax
    rect_l = float(px1 - px0)
    rect_w = float(py1 - py0)

    # Optional a-Si bbox (to restrict holes to overhang region in Y and/or X)
    asi_y_range: tuple[float, float] | None = None
    asi_x_range: tuple[float, float] | None = None
    if r_asi is not None:
        ax0, ay0, ax1, ay1 = bbox_xyxy(r_asi)
        asi_y_range = (ay0, ay1)
        asi_x_range = (ax0, ax1)

    # 6) Release holes (FINAL frame)
    if holes.add_holes:
        # Sample the centerline robustly
        s_vals = np.linspace(0.0, path_length_um(P), 4000)
        pts_final = sample_points_um(P, s_vals)

        # If SiN/oxide were shifted, shift the keep-out path the same amount
        dy = float(getattr(serp, "y_offset_um", 0.0) or 0.0)
        if dy != 0.0:
            pts_final[:, 1] += dy

        # Build clipping windows (limit to a-Si region if present)
        x_range = asi_x_range
        y_range = asi_y_range

        add_release_rows_at_seams_final_frame(
            comp=D,
            P=P,
            plate_bbox_xyxy=(bxmin, bymin, bxmax, bymax),
            layers=layers,
            holes=holes,
            widths=widths,
            sample_N=4000,
            straight_tol=0.06,
            bend_trim_um=2.0,
            mx_margin=plate.mx_margin,
            my_margin=plate.my_margin,
            pts_final=pts_final,
            x_range=x_range,
            y_range=y_range,
        )

    # Helper: bottom-strip window (between plate bottom and a-Si bottom)
    def _bottom_strip_window(
        *,
        side_margin_um: float = 0.0,
        symmetric_margin_um: float = 0.0,  # equal gap from plate bottom and a-Si bottom
        fixed_height_um: float | None = None,
    ) -> tuple[float, float, float, float] | None:
        # plate bbox available in scope: px0, py0, px1, py1
        xL = px0 + side_margin_um
        xR = px1 - side_margin_um
        if xR <= xL:
            return None

        if r_asi is not None:
            ax0, ay0, ax1, ay1 = bbox_xyxy(r_asi)
            # vertical window between plate bottom and a-Si bottom
            y0 = py0 + symmetric_margin_um
            y1 = ay0 - symmetric_margin_um
            if fixed_height_um is not None:
                mid = 0.5 * (y0 + y1)
                y0 = mid - 0.5 * fixed_height_um
                y1 = mid + 0.5 * fixed_height_um
        else:
            # no a-Si: just use fixed height above plate bottom
            y0 = py0 + symmetric_margin_um
            y1 = y0 + (fixed_height_um or 40.0)

        if y1 <= y0:
            return None

        return (xL, y0, xR - xL, y1 - y0)

    # 6.6) Two oxide rectangles covering the bottom strip region
    ws = _bottom_strip_window(
        side_margin_um=0.0,          # no side margin
        symmetric_margin_um=0.0,     # equal margin to plate bottom and a-Si bottom
        fixed_height_um=None,        # None => full gap between plate bottom and a-Si bottom
    )
    if ws is not None:
        xL, y0, w, h = ws
        # lower oxide (between M1 and stack)
        ox_lower = gf.components.rectangle(size=(w, h), layer=layers.OX_LOWER_STRIP)
        D.add_ref(ox_lower).move((xL, y0))
        # upper oxide (cap over stack; same strip window)
        ox_upper = gf.components.rectangle(size=(w, h), layer=layers.OX_UPPER_STRIP)
        D.add_ref(ox_upper).move((xL, y0))

        # --- M1 centered with symmetric inner margins inside this same window ---
        INNER_MARGIN = 20.0   # equal clearance above/below M1 inside the strip
        m1_h = max(0.0, h - 2 * INNER_MARGIN)
        y_center = y0 + 0.5 * h
        y0_m1 = y_center - 0.5 * m1_h
        m1_rect = gf.components.rectangle(size=(w, m1_h), layer=layers.M1)
        D.add_ref(m1_rect).move((xL, y0_m1))

    # 7) Metadata for sidecar JSON
    meta: dict[str, Any] = {
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
        "serpentine": serp.model_dump(),
    }

    # Record strip layers
    meta["layers"]["OxideLowerStrip"] = {
        "gds_layer": layers.OX_LOWER_STRIP[0],
        "datatype": layers.OX_LOWER_STRIP[1],
        "region": "bottom_strip_window",
    }
    meta["layers"]["OxideUpperStrip"] = {
        "gds_layer": layers.OX_UPPER_STRIP[0],
        "datatype": layers.OX_UPPER_STRIP[1],
        "region": "bottom_strip_window",
    }
    meta["layers"]["M1"] = {
        "gds_layer": layers.M1[0],
        "datatype": layers.M1[1],
        "region": "bottom_strip_window",
        "inner_margin_um": 5.0,   # informational only
        "outer_margin_um": 0.0,
        "full_width": True,
    }

    return D, meta
