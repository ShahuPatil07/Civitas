"""Restricted cognition port, deliberately weak enumerator, reproducible runs."""
from copy import deepcopy
import json
from pathlib import Path
import random

from . import RULE_VERSION
from .benchmarks import instantiate, outcome
from .model import Action, canonical
from .world import World


class BudgetExhausted(Exception):
    pass


class AgentPort:
    """Only expose this port and the public task to an external reasoning adapter."""
    def __init__(self, world: World, task: dict):
        self.__world = world
        self.__task = deepcopy(task)

    def view(self) -> dict:
        return self.__world.view(self.__task["actor"])

    def submit(self, kind: str, args: dict) -> dict:
        history = self.__world.history
        if len(history) >= self.__task["max_actions"]:
            raise BudgetExhausted("action budget exhausted")
        if kind == "experiment" and sum(e["action"]["kind"] == "experiment" for e in history) >= self.__task["max_experiments"]:
            raise BudgetExhausted("experiment budget exhausted")
        event = self.__world.submit(Action(self.__task["actor"], kind, args))
        # Do not disclose state patches, other agents, or the researcher digest.
        return deepcopy({k: event[k] for k in ("id", "accepted", "evaluations", "metadata")})


def baseline(port: AgentPort, task: dict) -> None:
    """Bounded enumeration, no truth snapshots, benchmark IDs or solution plans.

    Samples known stock with one geometry, pairwise relations and single-edge work. Does not
    backtrack, diagnose, design, reset loads or search multi-step motion cycles.
    """
    rng = random.Random(task["seed"])

    def attempt(kind: str, args: dict) -> bool:
        if kind not in port.view()["allowed_actions"]:
            return True
        try:
            port.submit(kind, args)
            return True
        except BudgetExhausted:
            return False

    if not attempt("observe", {"target": "nearby"}):
        return
    view = port.view()
    known_shaping = {k["claim"] for k in view["knowledge"]
                     if k["origin"] in {"initial", "experiment"} and k["value"] is True}
    stocks = sorted(m for m, amount in view["inventory"].items()
                    if amount > 0 and f"shape:{m}" in known_shaping)
    rng.shuffle(stocks)
    for material in stocks[:2]:
        if not attempt("shape", {"material": material, "mass": min(1, view["inventory"][material]), "length": 2, "radius": .25}):
            return
    observations = port.view()["observations"]
    identities = sorted(observations)
    candidates = []
    # All pairwise compositions; compatibility is judged by the kernel.
    for left in identities:
        for right in identities:
            if left == right:
                continue
            for role in ("force", "rotation", "support", "contain"):
                candidates.append(("connect", {"a": left, "b": right, "kind": role}))
    rng.shuffle(candidates)
    # Reserve attempts for actual motion and measurements.
    for kind, args in candidates[:max(0, task["max_actions"] // 2)]:
        if not attempt(kind, args):
            return
    motions = []
    for target in identities:
        obj = observations[target]["object"]
        displacement = (1.0, 0.0)
        for c in task["goals"]:
            if c["subject"] == target and c["measure"] in {"x", "z"} and c["op"] == ">=":
                displacement = (max(0, c["value"] - obj["position"][0]), 0) if c["measure"] == "x" else (0, max(0, c["value"] - obj["position"][1]))
                break
            if c["subject"] == target and c["measure"] == "crossings":
                displacement = (0, c["parameters"]["upper"] - obj["position"][1])
        dx, dz = displacement
        motions.append(("move", {"target": target, "dx": dx, "dz": dz, "duration": 10}))
        for source in identities:
            if source != target and "source" in observations[source]["object"]:
                for mode in ("force", "rotation"):
                    motions.append(("work", {"path": [source, target], "mode": mode, "dx": dx, "dz": dz, "duration": 10}))
    rng.shuffle(motions)
    for kind, args in motions:
        if not attempt(kind, args):
            return
    if task["max_experiments"]:
        attempt("experiment", {"experiment": {"question": "Do the observed outcomes meet the task constraints?",
                                                 "design": None, "constraints": task["goals"]}})


def run(spec: dict, seed: int | None = None, solver: str = "baseline") -> dict:
    world, task = instantiate(spec, seed)
    if solver == "baseline":
        policy = baseline
    elif solver == "composition":
        from .composition import search
        policy = search
    else:
        raise ValueError(f"unknown solver: {solver}")
    policy(AgentPort(world, task), task)
    return {"format": "civitas-run-1", "rule_version": RULE_VERSION, "solver": solver, "scenario": deepcopy(spec),
            "task": task, "genesis": world.genesis, "events": world.history,
            "final_hash": world.state_hash, "outcome": outcome(world, task)}


def replay(record: dict) -> World:
    if record.get("format") != "civitas-run-1" or record.get("rule_version") != RULE_VERSION:
        raise ValueError("unsupported run format/rule version")
    # Bind genesis and evaluator to the scenario, not just to a supplied digest.
    world, task = instantiate(record["scenario"], record["task"]["seed"])
    if world.genesis != record["genesis"] or task != record["task"]:
        raise ValueError("scenario/genesis/task mismatch")
    for expected in record["events"]:
        actual = world.submit(Action.from_dict(expected["action"]))
        if actual != expected:
            raise ValueError(f"replay divergence at event {expected.get('sequence')}")
    if world.state_hash != record["final_hash"] or outcome(world, task) != record["outcome"]:
        raise ValueError("final state or outcome mismatch")
    return world


def save(record: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return path


def trace(record: dict) -> str:
    lines = [f"{record['task']['id']} | solver={record['solver']} | seed={record['task']['seed']}"]
    for event in record["events"]:
        action = event["action"]
        lines.append(f"{event['sequence']:03d} {'ACCEPT' if event['accepted'] else 'REJECT'} {action['kind']} {canonical(action['args'])}")
        lines.append(f"    event {event['id']} | {len(event['effects'])} state changes | {event['state_hash'][:12]}")
        for evaluation in event["evaluations"]:
            lines.append(f"    {evaluation['status']}: {evaluation['code']}: {evaluation['reason']}")
        if event["metadata"]:
            lines.append("    outcome " + canonical(event["metadata"]))
    for evaluation in record["outcome"]["constraints"]:
        lines.append(f"GOAL {evaluation['status']}: {evaluation['reason']}")
    lines.append(f"SUCCESS={record['outcome']['success']} attempts={record['outcome']['attempts']} experiments={record['outcome']['experiments']} within_budget={record['outcome']['within_budget']}")
    lines.append("FINAL " + record["final_hash"])
    return "\n".join(lines)
