# examples/build_design2.py
from __future__ import annotations
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


def main() -> None:
    d = DeviceDefaults()  # start from library defaults

    # --- Serpentine (Design 2) ---
    # Paper: NL = 19 loops  -> iterations ~ 2*NL = 38 (same convention as Design 1: 12 -> ~6 loops)
    d.serpentine.iterations   = 38      # ~19 S/U-motif loops total
    d.serpentine.radius_um    = 6.05    # Euler bend radius (R)
    d.serpentine.length_um    = 60.0    # straight segment length (Ls)

    # Constrain vertical footprint to the a-Si window from the paper
    d.serpentine.band_height_um = 80.0  # released band height (µm)
    d.serpentine.y_margin_um    = 0.0   # equal clearance top/bottom inside that band

    d.serpentine.y_offset_um = -14.0   # example: move WG+oxide down by 10 µm


    # --- Plate (Al/AlN/Al) ---
    # Paper footprint: ~100 x 650 µm (X x Y)
    d.plate.mstack_rect_length_um = 650.0  # along X (cantilever length direction)
    d.plate.mstack_rect_width_um  = 100.0  # along Y (span across the serpentine)
    d.plate.mx_margin             = 2.0
    d.plate.my_margin             = 2.0

    # --- a-Si overhang (released region) ---
    # Overhang h = 80 µm (matches band_height_um above)
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

    # --- Output file ---
    d.build.gds_path = "design2_serpentine_multilayer.gds"

    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=d.serpentine,
        widths=d.widths,
        plate=d.plate,
        asi=d.asi,
        holes=d.holes,
        build=d.build,
    )
    out = write_gds_with_meta(comp, meta, d.build.gds_path)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
