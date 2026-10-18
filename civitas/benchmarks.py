"""Scenario initialization and outcome evaluation, independent of the solver."""
from copy import deepcopy
from importlib.resources import files
import json
from uuid import NAMESPACE_URL, uuid5

from . import RULE_VERSION
from .constraints import validate_constraint
from .materials import catalog
from .model import digest, keys, uid
from .world import World


def available() -> list[str]:
    return sorted(p.name[:-5] for p in files("benchmarks").iterdir() if p.name.endswith(".json"))


def load(name: str) -> dict:
    if name not in available():
        raise ValueError(f"unknown benchmark {name!r}; choose from {', '.join(available())}")
    return json.loads(files("benchmarks").joinpath(name + ".json").read_text(encoding="utf-8"))


def instantiate(spec: dict, seed: int | None = None) -> tuple[World, dict]:
    """Trusted genesis builder. Names resolve input data; laws see only properties."""
    spec = deepcopy(spec)
    keys(spec, {"id", "description", "seed", "universe", "stocks", "objects", "agent", "goals",
                "max_actions", "max_experiments", "allowed_actions"}, {"materials", "rule_version", "agent_positions"})
    if not isinstance(spec["id"], str) or not isinstance(spec["description"], str):
        raise ValueError("scenario id and description must be text")
    for budget in ("max_actions", "max_experiments"):
        if type(spec[budget]) is not int or spec[budget] < 0:
            raise ValueError("budgets must be nonnegative integers")
    seed = spec["seed"] if seed is None else seed
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    if not isinstance(spec["goals"], list) or not spec["goals"]:
        raise ValueError("benchmark must have nonempty goals")
    namespace = str(uuid5(NAMESPACE_URL, "civitas/scenario/" + digest({"spec": spec, "seed": seed})))
    mats = spec.get("materials", catalog())
    labels = {m["label"]: identity for identity, m in mats.items()}
    symbols = {name: uid(namespace, "object/" + name) for name in spec["objects"]}
    symbols["agent"] = uid(namespace, "agent/0")
    universe = {"gravity": 9.81, "observation_radius": 20, "transfer_efficiency": .9}
    universe.update(spec["universe"])
    objects = {}
    for name, definition in spec["objects"].items():
        keys(definition, {"material", "mass", "length", "radius", "position"}, {"source"})
        obj = deepcopy(definition)
        obj["material"] = labels.get(obj["material"], obj["material"])
        obj.update(angle=0, environment_work=0, human_work=0, motions=[])
        objects[symbols[name]] = obj
    keys(spec["agent"], {"energy", "power", "max_force", "known_shaping"})
    if not isinstance(spec["agent"]["known_shaping"], list):
        raise ValueError("known_shaping must be a list of material references")
    inventory = {labels.get(name, name): mass for name, mass in spec["stocks"].items()}
    knowledge = [{"claim": f"shape:{labels.get(name, name)}", "value": True, "confidence": 1,
                  "evidence": [], "origin": "initial"} for name in spec["agent"]["known_shaping"]]
    agents = {}
    for i in range(5):
        identity = uid(namespace, f"agent/{i}")
        agents[identity] = {"position": spec.get("agent_positions", [[0, 0]] * 5)[i], "energy": spec["agent"]["energy"],
                            "power": spec["agent"]["power"], "max_force": spec["agent"]["max_force"],
                            "effort_spent": 0, "inventory": deepcopy(inventory) if i == 0 else {},
                            "knowledge": deepcopy(knowledge) if i == 0 else [], "observations": {}}
    goals = deepcopy(spec["goals"])
    for c in goals:
        c["subject"] = symbols.get(c["subject"], c["subject"])
        validate_constraint(c)
    genesis = {"rule_version": RULE_VERSION, "world_id": namespace, "seed": seed, "universe": universe,
               "materials": mats, "objects": objects, "agents": agents, "relations": {}, "designs": {},
               "ideas": {}, "experiments": {}, "time": 0, "allowed_actions": spec["allowed_actions"]}
    if spec.get("rule_version"):
        genesis["rule_version"] = spec["rule_version"]
        genesis["projects"] = {}
    world = World(genesis)
    public = {"id": spec["id"], "description": spec["description"], "actor": symbols["agent"],
              "goals": goals, "max_actions": spec["max_actions"], "max_experiments": spec["max_experiments"], "seed": seed}
    return world, public


def outcome(world: World, task: dict) -> dict:
    results = [world.evaluate(c) for c in task["goals"]]
    attempts = len(world.history)
    experiments = sum(e["action"]["kind"] == "experiment" for e in world.history)
    within_budget = attempts <= task["max_actions"] and experiments <= task["max_experiments"]
    return {"success": bool(results) and within_budget and all(r["status"] == "satisfied" for r in results),
            "constraints": results, "attempts": attempts, "experiments": experiments, "within_budget": within_budget}
