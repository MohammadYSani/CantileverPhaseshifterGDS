# src/piezo_pic/tech/params.py
from __future__ import annotations

from pydantic import BaseModel, Field

# ============================================================
#   Serpentine waveguide geometry
# ============================================================

class SerpentineParams(BaseModel):
    """Parameters for generating the serpentine waveguide path."""
    iterations: int = Field(12, ge=1, description="Number of bend–straight motifs")
    radius_um: float = 15.0
    length_um: float = 60.0
    npts_per_bend: int = Field(300, ge=8, description="Sampling points per Euler bend")
    y_offset_um: float = 0.0  # vertical shift applied to SiN + oxide after extrusion

    # --- optional fields (default off) ---
    band_height_um: float | None = Field(
        None,
        description="If set, force the serpentine to fit inside this vertical window (µm).",
    )
    y_margin_um: float = Field(
        0.0,
        ge=0.0,
        description="Equal clearance from top and bottom edges of the band_height window.",
    )


# ============================================================
#   Waveguide cross-section widths
# ============================================================

class WaveguideWidths(BaseModel):
    """Core/cladding widths for the waveguide path."""
    width_sin_um: float = 0.40
    width_oxide_um: float = 1.50
    add_oxide: bool = True


# ============================================================
#   Plate (Al/AlN/Al) stack parameters
# ============================================================

class PlateParams(BaseModel):
    """Dimensions and placement of the Al/AlN/Al plate stack."""
    mstack_rect_length_um: float | None = None  # None -> auto span
    mstack_rect_width_um: float = 6.0
    mstack_rect_dx_um: float = 0.0
    mstack_rect_dy_um: float = -25.0
    mx_margin: float = 10.0
    my_margin: float = 0.0


# ============================================================
#   a-Si overhang (cantilever)
# ============================================================

class ASiParams(BaseModel):
    add_asi: bool = True
    asi_rect_width_um: float = 30.0
    asi_overhang_left_um: float = 0.0
    asi_rect_dx_um: float = 0.0
    asi_rect_dy_um: float = 0.0
    overhang_x_um: float | None = None   # NEW: cantilever length along X


# ============================================================
#   Release-hole pattern
# ============================================================

class HoleParams(BaseModel):
    add_holes: bool = True
    hole_diam_um: float = 3.0
    hole_pitch_um: float = 3.0
    holes_per_row: int = 6
    avoid_clearance_um: float = 0.20

    # vertical control
    hole_pitch_y_um: float | None = None
    holes_per_col: int | None = None

    # NEW: trim hole rows away from the overhang/clamp boundary
    edge_clearance_y_um: float = 0.0   # e.g. 5.0 removes the first/last row near the Y edges


# ============================================================
#   Oxide backing / clamp region
# ============================================================

class BackingParams(BaseModel):
    add_backing: bool = True
    clamp_height_um: float = 40.0      # y-dimension in layout
    thickness_um: float = 2.0          # z-dimension for simulation
    material: str = "SiO2"


# ============================================================
#   Build-time / I/O control
# ============================================================

class BuildParams(BaseModel):
    """Build-time options (mostly I/O)."""
    gds_path: str = "serpentine_multilayer.gds"

    # NEW: controls equal clearance above/below M1 inside the bottom strip window.
    # Set to 0.0 to make M1 span the entire oxide strip (used in Design 2).
    m1_inner_margin_um: float = 20.0


# ============================================================
#   Aggregate default container
# ============================================================

class DeviceDefaults(BaseModel):
    """Top-level container for all parameter groups with defaults."""
    serpentine: SerpentineParams = SerpentineParams()
    widths: WaveguideWidths = WaveguideWidths()
    plate: PlateParams = PlateParams()
    asi: ASiParams = ASiParams()
    holes: HoleParams = HoleParams()
    backing: BackingParams = BackingParams()   # <-- NEW
    build: BuildParams = BuildParams()
