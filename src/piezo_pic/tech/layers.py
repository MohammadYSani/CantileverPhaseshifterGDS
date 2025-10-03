# src/piezo_pic/tech/layers.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias

# GDSII layer/datatype pair
GdsLayer: TypeAlias = tuple[int, int]

# --- Default layer map (edit to match your PDK) ---
L_SIN: GdsLayer       = (1, 0)    # SiN core (serpentine)
L_AL_BOTTOM: GdsLayer = (2, 0)    # Bottom Aluminum
L_ALN: GdsLayer       = (3, 0)    # Aluminum Nitride
L_AL_TOP: GdsLayer    = (4, 0)    # Top Aluminum
L_OXIDE: GdsLayer     = (5, 0)    # Oxide cladding that follows the serpentine
L_ASI: GdsLayer       = (6, 0)    # Amorphous-Si cantilever overhang (rectangle)
L_RELEASE: GdsLayer   = (10, 0)   # Release holes
L_M1: GdsLayer        = (20, 0)   # Metal pad
L_OX_LOWER_STRIP: GdsLayer = (31, 0)   # oxide between M1 and the metal stack (bottom strip)
L_OX_UPPER_STRIP: GdsLayer = (32, 0)   # oxide cap above the stack (bottom strip)


@dataclass(frozen=True)
class LayerMap:
    """
    Immutable container for all layers used in this PDK/tech file.
    Each field is a (layer, datatype) pair for GDSII.
    """
    SIN: GdsLayer = L_SIN
    AL_BOTTOM: GdsLayer = L_AL_BOTTOM
    ALN: GdsLayer = L_ALN
    AL_TOP: GdsLayer = L_AL_TOP
    OXIDE: GdsLayer = L_OXIDE
    ASI: GdsLayer = L_ASI
    RELEASE: GdsLayer = L_RELEASE
    M1: GdsLayer = L_M1
    OX_LOWER_STRIP: GdsLayer = L_OX_LOWER_STRIP
    OX_UPPER_STRIP: GdsLayer = L_OX_UPPER_STRIP

# Default global instance
DEFAULT_LAYERS = LayerMap()
