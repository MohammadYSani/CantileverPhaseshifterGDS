# examples/build_design2_with_backing.py
from __future__ import annotations

import gdsfactory as gf

from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults
from piezo_pic.utils.geometry import bbox_xyxy


def _info_to_dict(info_obj) -> dict:
    """Safely coerce gdsfactory/kfactory Info or pydantic models to dict."""
    if info_obj is None:
        return {}
    for attr in ("model_dump", "dict"):
        fn = getattr(info_obj, attr, None)
        if callable(fn):
            try:
                return dict(fn())
            except Exception:
                pass
    if isinstance(info_obj, dict):
        return info_obj
    try:
        return dict(info_obj)
    except Exception:
        return {}


def add_clamp_backing(
    comp: gf.Component,
    plate_w_um: float,
    clamp_height_um: float,
    L_BACKING: tuple[int, int],
) -> gf.Component:
    """
    Make a new top cell, insert 'comp', and add a backing/clamp rectangle
    directly under the plate bottom with the given height.
    """
    top = gf.Component("design2_with_backing")
    top << comp

    xmin, ymin, xmax, ymax = bbox_xyxy(comp)
    plate_x0 = xmin           # plate starts at left edge of device
    plate_y0 = ymin           # plate bottom Y (since plate is lowest in stack)

    clamp = gf.components.rectangle(size=(plate_w_um, clamp_height_um), layer=L_BACKING)
    (top << clamp).move((plate_x0, plate_y0 - clamp_height_um))

    # carry metadata forward (convert Info/pydantic to dict first)
    top.info.update(_info_to_dict(getattr(comp, "info", None)))
    top.info["added_clamp_um"] = float(clamp_height_um)
    top.info["bbox_um_with_clamp"] = (xmin, plate_y0 - clamp_height_um, xmax, ymax)
    return top


def main() -> None:
    d = DeviceDefaults()  # independent parameter set for Design 2

    # --- Serpentine (Design 2) ---
    d.serpentine.iterations     = 38
    d.serpentine.radius_um      = 6.05
    d.serpentine.length_um      = 60.0
    d.serpentine.band_height_um = 80.0
    d.serpentine.y_margin_um    = 0.0
    d.serpentine.y_offset_um    = -14.0

    # --- Plate (Al/AlN/Al) ---
    d.plate.mstack_rect_length_um = 650.0  # X span (cantilever length)
    d.plate.mstack_rect_width_um  = 100.0  # Y span
    d.plate.mx_margin             = 2.0
    d.plate.my_margin             = 2.0

    # --- a-Si overhang ---
    d.asi.add_asi              = True
    d.asi.asi_rect_width_um    = 80.0
    d.asi.asi_overhang_left_um = 0.0
    d.asi.asi_rect_dx_um       = 0.0
    d.asi.asi_rect_dy_um       = 0.0

    # --- Release holes ---
    d.holes.add_holes          = True
    d.holes.hole_diam_um       = 3.0
    d.holes.hole_pitch_um      = 10.0
    d.holes.avoid_clearance_um = 0.50
    d.holes.holes_per_col      = 8
    d.holes.hole_pitch_y_um    = None

    # --- M1 control (inside bottom strip window) ---
    # 0.0 => M1 fills entire strip; increase to inset M1 equally from top/bottom.
    d.build.m1_inner_margin_um = 6.0

    # --- Output file ---
    d.build.gds_path = "design2_serpentine_multilayer.gds"

    # Build device (without backing yet)
    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=d.serpentine,
        widths=d.widths,
        plate=d.plate,
        asi=d.asi,
        holes=d.holes,
        build=d.build,
    )

    # Add backing/clamp if requested
    L_BACKING = DEFAULT_LAYERS.BACKING
    plate_w_um = float(d.plate.mstack_rect_length_um)
    top = (
        add_clamp_backing(
            comp,
            plate_w_um=plate_w_um,
            clamp_height_um=float(d.backing.clamp_height_um),
            L_BACKING=L_BACKING,
        )
        if d.backing.add_backing
        else comp
    )

    # Write GDS + metadata
    out = write_gds_with_meta(top, meta, d.build.gds_path)
    print(f"Wrote {out} and {out.with_suffix('.meta.json')}")


if __name__ == "__main__":
    main()
