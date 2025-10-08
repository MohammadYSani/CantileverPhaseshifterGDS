# examples/build_design1_with_clamp.py
from __future__ import annotations
import gdsfactory as gf

from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


def get_bbox_xyxy(c):
    """Robust across gdsfactory versions; uses per-axis properties."""
    try:
        return float(c.xmin), float(c.ymin), float(c.xmax), float(c.ymax)
    except Exception as e:
        raise ValueError("Component has no computed bbox; is it empty?") from e


def _info_to_dict(info_obj) -> dict:
    """Make kfactory/gdsfactory Info or pydantic models safe for dict-like use."""
    if info_obj is None:
        return {}
    for attr in ("model_dump", "dict"):  # pydantic v2 or v1
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
    plate_w: float,
    clamp_height_um: float,
    L_BACKING: tuple[int, int],
) -> gf.Component:
    """Create a new top cell, place comp, and add only the clamp/backing rectangle."""
    top = gf.Component("design1_with_clamp")
    top << comp

    xmin, ymin, xmax, ymax = get_bbox_xyxy(comp)
    plate_x0 = xmin
    plate_y0 = ymin

    # Add the clamp/backing rectangle (layer BACKING -> L_OX_BACKING)
    clamp = gf.components.rectangle(size=(plate_w, clamp_height_um), layer=L_BACKING)
    (top << clamp).move((plate_x0, plate_y0 - clamp_height_um))

    # Metadata
    top.info.update(_info_to_dict(comp.info))
    top.info["added_clamp_um"] = float(clamp_height_um)
    top.info["bbox_um_with_clamp"] = (xmin, plate_y0 - clamp_height_um, xmax, ymax)

    return top


def main() -> None:
    d = DeviceDefaults()  # start from library defaults

    # --- Serpentine (Design 1) ---
    d.serpentine.iterations = 12
    d.serpentine.radius_um = 9.5
    d.serpentine.length_um = 270.0

    # --- Plate (Al/AlN/Al) ---
    d.plate.mstack_rect_length_um = 325.0  # Y (height)
    d.plate.mstack_rect_width_um = 350.0   # X (span)
    d.plate.mx_margin = 2.0
    d.plate.my_margin = 2.0

    # --- a-Si overhang ---
    d.asi.add_asi = True
    d.asi.asi_rect_width_um = 300.0
    d.asi.asi_overhang_left_um = 0.0
    d.asi.asi_rect_dx_um = 0.0
    d.asi.asi_rect_dy_um = 0.0

    # --- Release holes ---
    d.holes.add_holes = True
    d.holes.hole_diam_um = 3.0
    d.holes.hole_pitch_um = 10.0
    d.holes.avoid_clearance_um = 0.20
    d.holes.holes_per_col = 12
    d.holes.hole_pitch_y_um = None

    # ---------------------------------------------------------------------
    # Build your existing device cell
    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=d.serpentine,
        widths=d.widths,
        plate=d.plate,
        asi=d.asi,
        holes=d.holes,
        build=d.build,
    )

    plate_w = float(d.plate.mstack_rect_length_um)
    L_BACKING = DEFAULT_LAYERS.BACKING   # maps to L_OX_BACKING in your LayerMap

    # Optionally add the clamp/backing based on params
    if d.backing.add_backing:
        top = add_clamp_backing(
            comp,
            plate_w=plate_w,
            clamp_height_um=float(d.backing.clamp_height_um),
            L_BACKING=L_BACKING,
        )
    else:
        top = comp

    # ---------------------------------------------------------------------
    # Output single SIM GDS
    sim_path = "design1_serpentine_multilayer_with_clamp.gds"
    top.write_gds(sim_path)
    print(f"Wrote {sim_path}")

    write_gds_with_meta(top, _info_to_dict(meta), sim_path)


if __name__ == "__main__":
    main()
