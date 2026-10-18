"""Small quasistatic laws. Labels and benchmark identities are never inspected."""
from math import hypot
from .affordances import permitted


def properties(obj: dict, materials: dict) -> dict:
    material = materials[obj["material"]]
    area = obj["mass"] / material["density"] / obj["length"]
    return {"section": area, "volume": obj["mass"] / material["density"],
            "tension_capacity": area * material["tensile_strength"],
            "compression_capacity": area * material["compressive_strength"],
            "friction": material["friction"], "mass": obj["mass"],
            "length": obj["length"], "radius": obj["radius"],
            "source_power": obj.get("source", {}).get("power", 0)}


def distance(a: dict, b: dict) -> float:
    return hypot(a["position"][0] - b["position"][0], a["position"][1] - b["position"][1])


def relation_capacity(a: dict, b: dict, kind: str, materials: dict, span: float = 0) -> float:
    pa, pb = properties(a, materials), properties(b, materials)
    if kind in {"support", "contain"}:
        # Coarse load-bearing proxy, explicitly not beam theory.
        return pa["compression_capacity"] / (1 + (span / a["length"]) ** 2)
    capacity = min(pa["tension_capacity"], pb["tension_capacity"])
    if kind == "rotation":
        return capacity * min(a["radius"], b["radius"])
    return capacity


def affordances(obj: dict, materials: dict) -> list[str]:
    return [a.name for a in permitted(properties(obj, materials))]


def motion_requirements(obj: dict, dx: float, dz: float, materials: dict, gravity: float) -> dict:
    horizontal = abs(dx)
    upward = max(0, dz)
    friction_force = properties(obj, materials)["friction"] * obj["mass"] * gravity
    path = hypot(dx, dz)
    work = friction_force * horizontal + obj["mass"] * gravity * upward
    # Lowering is controlled but dissipative: weight must still be held.
    force = (friction_force * horizontal + obj["mass"] * gravity * abs(dz)) / path if path else 0
    return {"distance": path, "force": force, "work": work}
