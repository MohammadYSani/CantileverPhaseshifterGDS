# examples/build_design1.py
from __future__ import annotations
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import (
    DeviceDefaults, SerpentineParams, WaveguideWidths,
    PlateParams, ASiParams, HoleParams, BuildParams
)
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


def main():
    d = DeviceDefaults()

    # Copy defaults so we don’t mutate shared state
    serp   = SerpentineParams(**d.serpentine.model_dump())
    widths = WaveguideWidths(**d.widths.model_dump())
    plate  = PlateParams(**d.plate.model_dump())
    asi    = ASiParams(**d.asi.model_dump())
    holes  = HoleParams(**d.holes.model_dump())
    build  = BuildParams(**d.build.model_dump())

    # --- Design 1 (DC / high-displacement) ---
    # About ~6 loops, ~15 µm bends, ~60 µm straights
    serp.iterations    = 6
    serp.radius_um     = 15.0
    serp.length_um     = 60.0
    serp.npts_per_bend = 300

    # Plate footprint: autosize X, clamp Y ~325 µm, add margins
    plate.mstack_rect_length_um = None
    plate.mstack_rect_width_um  = 325.0
    plate.mx_margin             = 2.0
    plate.my_margin             = 2.0

    # a-Si released region: match plate width, extend 300 µm to the LEFT
    asi.add_asi              = True
    asi.asi_rect_width_um    = 1e6
    asi.asi_overhang_left_um = 300.0
    asi.asi_rect_dx_um       = 0
    asi.asi_rect_dy_um       = 0.0

    # Release holes
    holes.add_holes      = True
    holes.hole_diam_um   = 3.0
    holes.hole_pitch_um  = 10.0
    holes.holes_per_row  = 11
    holes.avoid_clearance_um = 0.20

    # Orientation and output
    build.rotate_deg = 270.0
    build.gds_path   = "design1_serpentine_multilayer.gds"

    # Build & write
    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=serp, widths=widths, plate=plate, asi=asi, holes=holes, build=build
    )
    out = write_gds_with_meta(comp, meta, build.gds_path)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
