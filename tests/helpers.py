from civitas.benchmarks import instantiate
from civitas.model import Action


def spec():
    return {
        "id": "calibration", "description": "Displace a measured load.", "seed": 42,
        "universe": {"gravity": 9.81}, "stocks": {"wood": 10, "water": 2},
        "agent": {"energy": 10000, "power": 2000, "max_force": 2000, "known_shaping": ["wood", "water"]},
        "objects": {
            "boundary": {"material": "iron", "mass": 50, "length": 5, "radius": .5, "position": [0, 0],
                         "source": {"energy": 10000, "power": 2000, "max_force": 2000}},
            "load": {"material": "stone", "mass": 10, "length": .5, "radius": .5, "position": [1, 0]},
        },
        "goals": [{"category": "physical", "measure": "x", "subject": "load", "op": ">=", "value": 2}],
        "max_actions": 100, "max_experiments": 5,
        "allowed_actions": ["observe", "shape", "connect", "move", "work", "experiment", "record_design", "record_idea", "believe"],
    }


def fixture(config=None):
    w, task = instantiate(config or spec())
    actor = task["actor"]
    load = task["goals"][0]["subject"]
    source = next(i for i, o in w.snapshot()["objects"].items() if "source" in o)
    return w, task, actor, source, load


def act(world, actor, operation, **args):
    return world.submit(Action(actor, operation, args))


def material(world, label):
    return next(i for i, m in world.snapshot()["materials"].items() if m["label"] == label)


def constraint(subject, measure, value, category="physical", op=">=", **parameters):
    c = {"category": category, "subject": subject, "measure": measure, "op": op, "value": value}
    if parameters:
        c["parameters"] = parameters
    return c


def design():
    return {"title": "Candidate alpha", "components": [{"key": "a", "requirements": []}, {"key": "b", "requirements": []}],
            "relationships": [{"kind": "force", "a": "a", "b": "b"}], "required_properties": [],
            "intended_functions": ["transfer force"], "constraints": [], "construction_steps": [],
            "assumptions": ["capacities remain sufficient"], "failure_modes": ["insufficient strength"],
            "evidence": [], "version": 1, "parent": None}
