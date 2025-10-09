# src/piezo_pic/__init__.py
"""
piezo_pic: PDK and utilities for piezo-optomechanical cantilever waveguides.

Public API:
- build_serpentine_multilayer_cell: construct the device component
- write_gds_with_meta: write GDS plus a metadata sidecar
- DEFAULT_LAYERS: canonical layer map
- Parameter models (pydantic): SerpentineParams, WaveguideWidths, PlateParams,
  ASiParams, HoleParams, BuildParams, DeviceDefaults
"""

from importlib import metadata as _metadata

try:  # populated if installed; during editable/dev installs this may be absent
    __version__ = _metadata.version("piezo-pic")
except _metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

# Public entry points
from .cells.serpentine_multilayer import build_serpentine_multilayer_cell
from .io.write import write_gds_with_meta

# Public tech surface
from .tech.layers import DEFAULT_LAYERS
from .tech.params import (
    ASiParams,
    BuildParams,
    DeviceDefaults,
    HoleParams,
    PlateParams,
    SerpentineParams,
    WaveguideWidths,
)

__all__ = [
    "build_serpentine_multilayer_cell",
    "write_gds_with_meta",
    "DEFAULT_LAYERS",
    "SerpentineParams",
    "WaveguideWidths",
    "PlateParams",
    "ASiParams",
    "HoleParams",
    "BuildParams",
    "DeviceDefaults",
    "__version__",
]
