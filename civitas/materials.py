"""Illustrative bulk properties, not engineering reference data (SI units)."""
from uuid import NAMESPACE_URL, uuid5

# density kg/m³, tensile/compressive Pa, sliding friction, shaping J/kg.
_ROWS = [
    ("wood", 600, 40e6, 30e6, .4, 20),
    ("stone", 2600, 3e6, 100e6, .7, 150),
    ("iron", 7800, 200e6, 200e6, .5, 300),
    ("steel", 7850, 400e6, 400e6, .5, 400),
    ("copper", 8960, 200e6, 70e6, .4, 200),
    ("glass", 2500, 30e6, 300e6, .3, 120),
    ("water", 1000, 0, 0, .05, 0),
    ("cloth", 300, 10e6, 0, .5, 5),
    ("rope", 700, 50e6, 0, .5, 10),
    ("soil", 1500, 0, 1e5, .8, 10),
]


def catalog() -> dict:
    return {
        str(uuid5(NAMESPACE_URL, f"civitas/material/v0/{name}")): {
            "label": name, "density": density, "tensile_strength": tensile,
            "compressive_strength": compression, "friction": friction,
            "shape_energy": cost,
        }
        for name, density, tensile, compression, friction, cost in _ROWS
    }
