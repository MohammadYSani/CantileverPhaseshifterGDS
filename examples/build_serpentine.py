# examples/build_serpentine.py
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import DeviceDefaults


def main() -> None:
    d = DeviceDefaults()  # all defaults in one place

    # --- Override release-hole density in MAIN ---
    d.holes.add_holes = True

    # Choose ONE:
    # A) Fixed count per column (simplest)
    d.holes.holes_per_col = 6
    d.holes.hole_pitch_y_um = None  # ensure pitch doesn't override

    # B) Or, pitch-based spacing (comment A out and use this instead)
    # d.holes.holes_per_col = None
    # d.holes.hole_pitch_y_um = 25.0  # µm between holes vertically

    # Optional: give the output a clearer name
    d.build.gds_path = "serpentine_multilayer.gds"

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
