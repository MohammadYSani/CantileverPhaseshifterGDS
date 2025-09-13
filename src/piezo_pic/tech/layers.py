# src/piezo_pic/tech/layers.py
from __future__ import annotations
from dataclasses import dataclass

# Tuple alias: (layer, datatype)
GdsLayer = tuple[int, int]

# --- Default layer map (edit to match your PDK) ---
L_SIN: GdsLayer      = (1, 0)    # SiN core (serpentine)
L_AL_BOTTOM: GdsLayer = (2, 0)   # Bottom Aluminum
L_ALN: GdsLayer       = (3, 0)   # Aluminum Nitride
L_AL_TOP: GdsLayer    = (4, 0)   # Top Aluminum
L_OXIDE: GdsLayer     = (5, 0)   # oxide cladding that follows the serpentine
L_ASI: GdsLayer       = (6, 0)   # amorphous-Si cantilever overhang (rectangle)
L_RELEASE: GdsLayer   = (10, 0)  # release holes
L_M1: GdsLayer        = (20, 0)  # metal pad

@dataclass(frozen=True)
class LayerMap:
    """Container for all layers used in this PDK/tech file."""
    SIN: GdsLayer = L_SIN
    AL_BOTTOM: GdsLayer = L_AL_BOTTOM
    ALN: GdsLayer = L_ALN
    AL_TOP: GdsLayer = L_AL_TOP
    OXIDE: GdsLayer = L_OXIDE
    ASI: GdsLayer = L_ASI
    RELEASE: GdsLayer = L_RELEASE
    M1: GdsLayer = L_M1

DEFAULT_LAYERS = LayerMap()
