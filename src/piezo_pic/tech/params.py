# src/piezo_pic/tech/params.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Tuple

class SerpentineParams(BaseModel):
    iterations: int = Field(12, ge=1)
    radius_um: float = 15.0
    length_um: float = 60.0
    npts_per_bend: int = Field(300, ge=8)

class WaveguideWidths(BaseModel):
    width_sin_um: float = 0.40
    width_oxide_um: float = 1.50
    add_oxide: bool = True

class PlateParams(BaseModel):
    mstack_rect_length_um: Optional[float] = None  # None -> auto span
    mstack_rect_width_um: float = 6.0
    mstack_rect_dx_um: float = 0.0
    mstack_rect_dy_um: float = 0.0
    mx_margin: float = 2.0
    my_margin: float = 2.0

class ASiParams(BaseModel):
    add_asi: bool = True
    asi_rect_width_um: float = 30.0
    asi_overhang_left_um: float = 0.0
    asi_rect_dx_um: float = 0.0
    asi_rect_dy_um: float = 0.0

class HoleParams(BaseModel):
    add_holes: bool = True
    hole_diam_um: float = 3.0
    hole_pitch_um: float = 3.0
    holes_per_row: int = 11   # fixed rows across seams
    avoid_clearance_um: float = 0.20  # extra keep-out beyond radius + hole/2

class BuildParams(BaseModel):
    rotate_deg: float = 270.0
    gds_path: str = "serpentine_multilayer.gds"

class DeviceDefaults(BaseModel):
    serpentine: SerpentineParams = SerpentineParams()
    widths: WaveguideWidths = WaveguideWidths()
    plate: PlateParams = PlateParams()
    asi: ASiParams = ASiParams()
    holes: HoleParams = HoleParams()
    build: BuildParams = BuildParams()
