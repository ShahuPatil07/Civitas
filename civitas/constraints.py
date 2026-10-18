"""Closed, data-driven measurable constraints; unknown is never success."""
from .model import keys, number
from .physics import properties

CATEGORIES = {"physical", "resource", "knowledge", "manufacturing", "economic", "social", "institutional"}
OPS = {">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b, "==": lambda a, b: a == b}


def result(status: str, code: str, reason: str, evidence=None, blocking=None) -> dict:
    return {"status": status, "code": code, "reason": reason,
            "evidence": evidence or {}, "blocking_requirements": blocking or []}


def validate_constraint(c: dict) -> None:
    keys(c, {"category", "measure", "subject", "op", "value"}, {"parameters"})
    if c["category"] not in CATEGORIES or c["op"] not in OPS:
        raise ValueError("invalid constraint category/comparator")
    if not isinstance(c["measure"], str) or not isinstance(c["subject"], str):
        raise ValueError("measure and subject must be strings")
    number(c["value"], "constraint value")
    if "parameters" in c and not isinstance(c["parameters"], dict):
        raise ValueError("constraint parameters must be a record")
    params = c.get("parameters", {})
    if c["measure"] == "crossings":
        keys(params, {"lower", "upper"})
        if number(params["upper"], "upper") <= number(params["lower"], "lower"):
            raise ValueError("crossing interval must be positive")
    elif c["measure"] == "known":
        keys(params, {"claim"})
        if not isinstance(params["claim"], str):
            raise ValueError("claim must be a string")
    elif c["measure"] == "stock_mass":
        keys(params, {"material"})
        if not isinstance(params["material"], str):
            raise ValueError("material must be a reference")
    elif params:
        raise ValueError("unexpected measure parameters")


def measure(state: dict, c: dict) -> float | None:
    category, name, subject = c["category"], c["measure"], c["subject"]
    if category not in {"physical", "resource", "knowledge"}:
        return None
    if category == "knowledge":
        agent = state["agents"].get(subject)
        if name != "known" or agent is None:
            return None
        return float(any(k["claim"] == c.get("parameters", {}).get("claim") for k in agent["knowledge"]))
    if category == "resource":
        if subject in state["agents"]:
            a = state["agents"][subject]
            if name == "stock_mass":
                material = c["parameters"]["material"]
                return a["inventory"].get(material, 0) if material in state["materials"] else None
            return a.get(name) if name in {"energy", "effort_spent"} else None
        obj = state["objects"].get(subject)
        return obj.get("source", {}).get("energy") if obj and name == "energy" else None
    obj = state["objects"].get(subject)
    if obj is None:
        return None
    if name in {"x", "z"}:
        return obj["position"][0 if name == "x" else 1]
    if name in {"mass", "length", "radius", "section", "volume", "tension_capacity", "compression_capacity", "friction"}:
        return properties(obj, state["materials"])[name]
    if name in {"environment_work", "human_work", "angle"}:
        return obj[name]
    if name == "crossings":
        lower, upper = c["parameters"]["lower"], c["parameters"]["upper"]
        armed, count = False, 0
        for motion in obj["motions"]:
            if motion["from"][1] <= lower:
                armed = True
            if armed and motion["to"][1] >= upper:
                count += 1
                armed = False
        return count
    if name == "bearing_span":
        return max((r["span"] for r in state["relations"].values()
                    if r["kind"] == "support" and r["b"] == subject and obj["position"][1] > 0), default=0)
    if name in {"supported_load", "supported_span"}:
        relations = [r for r in state["relations"].values() if r["kind"] == "support" and r["a"] == subject
                     and state["objects"][r["b"]]["position"][1] > 0]
        if name == "supported_span":
            return max((r["span"] for r in relations), default=0)
        return sum(state["objects"][r["b"]]["mass"] * state["universe"]["gravity"] for r in relations)
    return None


def evaluate(state: dict, c: dict) -> dict:
    validate_constraint(c)
    actual = measure(state, c)
    if actual is None:
        return result("unknown", "unmodeled_measure", "No modeled measurement is available", {"constraint": c}, [c])
    passed = OPS[c["op"]](actual, c["value"])
    return result("satisfied" if passed else "unsatisfied", "constraint_satisfied" if passed else "constraint_violation",
                  f"{c['measure']}: {actual:g} {c['op']} {c['value']:g}",
                  {"actual": actual, "constraint": c}, [] if passed else [c])
