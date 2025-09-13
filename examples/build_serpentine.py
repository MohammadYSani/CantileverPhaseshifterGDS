# examples/build_serpentine.py
from __future__ import annotations
from piezo_pic.tech.layers import DEFAULT_LAYERS
from piezo_pic.tech.params import (
    DeviceDefaults, SerpentineParams, WaveguideWidths, PlateParams,
    ASiParams, HoleParams, BuildParams
)
from piezo_pic.cells.serpentine_multilayer import build_serpentine_multilayer_cell
from piezo_pic.io.write import write_gds_with_meta


def main():
    defaults = DeviceDefaults()

    # Optionally override a few knobs here:
    serp = SerpentineParams(**defaults.serpentine.model_dump())
    widths = WaveguideWidths(**defaults.widths.model_dump())
    plate = PlateParams(**defaults.plate.model_dump())
    asi   = ASiParams(**defaults.asi.model_dump())
    holes = HoleParams(**defaults.holes.model_dump())
    build = BuildParams(**defaults.build.model_dump())

    # Example tweak:
    # holes.hole_diam_um = 2.0
    # build.gds_path = "serpentine12_multilayer_rectM_rot.gds"

    comp, meta = build_serpentine_multilayer_cell(
        layers=DEFAULT_LAYERS,
        serp=serp, widths=widths, plate=plate, asi=asi, holes=holes, build=build
    )
    out = write_gds_with_meta(comp, meta, build.gds_path)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
