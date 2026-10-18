"""Closed provider-independent cognitive outputs. Text never executes code."""
from copy import deepcopy
from .model import Action, Design, OPERATIONS, canonical, keys
from .constraints import validate_constraint

PHYSICAL_ACTIONS = {"observe", "shape", "connect", "move", "work", "disconnect"}
KINDS = {"intent", "hypothesis", "candidate_design", "design_revision", "plan", "action_proposal",
         "experiment_proposal", "diagnosis", "unresolved"}


def validate_physical_action(data):
    action = Action.from_dict(data)
    if action.kind not in PHYSICAL_ACTIONS:
        raise ValueError("model cannot submit administrative or arbitrary actions")
    keys(action.args, *OPERATIONS[action.kind])
    return action


def validate_proposal(data):
    keys(data, {"kind", "summary", "payload"})
    if data["kind"] not in KINDS or not isinstance(data["summary"], str) or not 1 <= len(data["summary"]) <= 2000:
        raise ValueError("unknown cognitive kind or invalid concise summary")
    p, kind = data["payload"], data["kind"]
    if not isinstance(p, dict):
        raise ValueError("payload must be an object")
    if kind == "intent":
        keys(p, {"goals"})
        if not isinstance(p["goals"], list) or not 1 <= len(p["goals"]) <= 12:
            raise ValueError("intent needs 1–12 measurable goals")
        for c in p["goals"]:
            validate_constraint(c)
    elif kind in {"candidate_design", "design_revision"}:
        keys(p, {"design"})
        d = Design.from_dict(p["design"])
        if len(d.construction_steps) > 32:
            raise ValueError("at most 32 actions per plan")
        for step in d.construction_steps:
            validate_physical_action(step)
    elif kind in {"plan", "action_proposal"}:
        keys(p, {"actions"})
        if not isinstance(p["actions"], list) or not 1 <= len(p["actions"]) <= 32:
            raise ValueError("plan needs 1–32 actions")
        for a in p["actions"]:
            validate_physical_action(a)
    elif kind == "experiment_proposal":
        keys(p, set())
    else:
        keys(p, {"requirements"})
        if not isinstance(p["requirements"], list) or not all(isinstance(x, str) for x in p["requirements"]):
            raise ValueError("requirements must be text references")
    canonical(data)
    return deepcopy(data)


def proposal(kind, summary, **payload):
    return validate_proposal({"kind": kind, "summary": summary, "payload": payload})
