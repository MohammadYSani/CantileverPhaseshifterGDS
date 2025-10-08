# src/piezo_pic/tech/layers.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TypeAlias

GdsLayer: TypeAlias = tuple[int, int]

L_SIN: GdsLayer       = (1, 0)
L_AL_BOTTOM: GdsLayer = (2, 0)
L_ALN: GdsLayer       = (3, 0)
L_AL_TOP: GdsLayer    = (4, 0)
L_OXIDE: GdsLayer     = (5, 0)
L_ASI: GdsLayer       = (6, 0)
L_RELEASE: GdsLayer   = (10, 0)
L_M1: GdsLayer        = (20, 0)
L_OX_LOWER_STRIP: GdsLayer = (31, 0)
L_OX_UPPER_STRIP: GdsLayer = (32, 0)

# NEW: clamp/backing layer used for the rectangular anchor under the plate
L_OX_BACKING: GdsLayer = (93, 0)

# (optional) legacy alias so older scripts referencing L_BACKING still work
L_BACKING: GdsLayer = L_OX_BACKING

@dataclass(frozen=True)
class LayerMap:
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
    # Keep the public field name BACKING for compatibility
    BACKING: GdsLayer = L_OX_BACKING

DEFAULT_LAYERS = LayerMap()
