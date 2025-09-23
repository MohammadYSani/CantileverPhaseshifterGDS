# examples/build_design1.py
from __future__ import annotations
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


def main() -> None:
    d = DeviceDefaults()  # start from library defaults

    # --- Serpentine (Design 1) ---
    d.serpentine.iterations = 12       # ~6 S-motifs
    d.serpentine.radius_um  = 9.5    # Euler bend radius
    d.serpentine.length_um  = 316.0    # straight section length

    # --- Plate (Al/AlN/Al) ---
    d.plate.mstack_rect_length_um = 325.0   # auto in X to cover the serpentine
    d.plate.mstack_rect_width_um  = 350.0  # total plate height (µm)
    d.plate.mx_margin             = 2.0
    d.plate.my_margin             = 2.0

    # --- a-Si overhang ---
    d.asi.add_asi              = True
    d.asi.asi_rect_width_um    = 300.0
    d.asi.asi_overhang_left_um = 0.0
    d.asi.asi_rect_dx_um       = 0.0   # edges aligned by the cell code
    d.asi.asi_rect_dy_um       = 0.0

    # --- Release holes: vertical columns at S seams ---
    d.holes.add_holes          = True
    d.holes.hole_diam_um       = 3.0
    d.holes.hole_pitch_um      = 10.0   # horizontal fallback (seams derived geometrically)
    d.holes.avoid_clearance_um = 0.20

    # vertical spacing (pick one style)
    d.holes.holes_per_col = 12          # fixed count per column
    d.holes.hole_pitch_y_um = None     # (or set, e.g., 25.0 µm, and clear holes_per_col)

    # Output file
    d.build.gds_path = "design1_serpentine_multilayer.gds"

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
