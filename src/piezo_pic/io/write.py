# src/piezo_pic/io/write.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import gdsfactory as gf


def write_gds_with_meta(
    comp: gf.Component,
    meta: dict[str, Any],
    gds_path: str | Path,
) -> Path:
    """Write a component to a GDS file and a sidecar JSON metadata file."""
    gds_path = Path(gds_path).with_suffix(".gds")
    gds_path.parent.mkdir(parents=True, exist_ok=True)  # ✅ ensure dir exists

    # ✅ handle both modern and old gdsfactory write methods
    write = getattr(comp, "write_gds", None)
    if callable(write):
        write(str(gds_path))
    else:
        gf.write_gds(comp, str(gds_path))

    meta_path = gds_path.with_suffix(".meta.json")
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False, default=str)  # ✅ default=str handles Path/datetime

    return gds_path
