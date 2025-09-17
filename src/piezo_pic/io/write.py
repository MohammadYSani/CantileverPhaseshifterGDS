# src/piezo_pic/io/write.py
from __future__ import annotations
from pathlib import Path
import json
import gdsfactory as gf
from typing import Dict, Any, Union


def write_gds_with_meta(
    comp: gf.Component,
    meta: Dict[str, Any],
    gds_path: Union[str, Path],
) -> Path:
    """
    Write a component to a GDS file and a sidecar JSON metadata file.

    Parameters
    ----------
    comp : gf.Component
        The component to write.
    meta : dict
        Metadata to save alongside the GDS.
    gds_path : str | Path
        Destination path (will be forced to `.gds` extension).

    Returns
    -------
    Path
        Path to the written `.gds` file.
    """
    gds_path = Path(gds_path).with_suffix(".gds")
    comp.write_gds(str(gds_path))

    meta_path = gds_path.with_suffix(".meta.json")
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    return gds_path
