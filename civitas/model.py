"""Data-only intermediate representations. No generated code is executable."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
import math
from typing import Any
from uuid import UUID, uuid5

OPERATIONS = {
    "inspect_resources": (set(), set()),
    "disconnect": ({"relation"}, set()),
    "start_project": ({"text", "target", "budgets", "use_knowledge"}, set()),
    "reason_project": ({"project", "proposal", "usage"}, set()),
    "step_project": ({"project"}, set()),
    "stop_project": ({"project", "reason"}, set()),
    "observe": ({"target"}, set()),
    "shape": ({"material", "mass", "length", "radius"}, set()),
    "connect": ({"a", "b", "kind"}, set()),
    "move": ({"target", "dx", "dz", "duration"}, set()),
    "work": ({"path", "dx", "dz", "duration"}, {"mode"}),
    "record_design": ({"design"}, set()),
    "record_idea": ({"idea"}, set()),
    "believe": ({"claim", "value", "confidence"}, set()),
    "experiment": ({"experiment"}, set()),
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def uid(namespace: str, key: str) -> str:
    return str(uuid5(UUID(namespace), key))


def number(value: Any, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return float(value)


def keys(data: dict, required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(data, dict) or required - data.keys() or data.keys() - required - optional:
        raise ValueError(f"expected fields {sorted(required)}, optional {sorted(optional)}")


def strings(value: Any, name: str) -> None:
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError(f"{name} must be a list of strings")


@dataclass(frozen=True)
class Action:
    actor: str
    kind: str
    args: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return deepcopy(asdict(self))

    @classmethod
    def from_dict(cls, data: dict) -> Action:
        keys(data, {"actor", "kind", "args"})
        if not isinstance(data["actor"], str) or not isinstance(data["kind"], str) or not isinstance(data["args"], dict):
            raise ValueError("invalid action envelope")
        canonical(data)
        return cls(**deepcopy(data))


@dataclass(frozen=True)
class Plan:
    intent: str
    actions: tuple[Action, ...]


@dataclass(frozen=True)
class Design:
    """A persisted hypothesis; components are local symbols, never new classes."""
    title: str
    components: list[dict]
    relationships: list[dict]
    required_properties: list[dict]
    intended_functions: list[str]
    constraints: list[dict]
    construction_steps: list[dict]
    assumptions: list[str]
    failure_modes: list[str]
    evidence: list[str]
    version: int = 1
    parent: str | None = None

    def to_dict(self) -> dict:
        return deepcopy(asdict(self))

    @classmethod
    def from_dict(cls, data: dict) -> Design:
        from .constraints import validate_constraint
        keys(data, {"title", "components", "relationships", "required_properties",
                    "intended_functions", "constraints", "construction_steps",
                    "assumptions", "failure_modes", "evidence", "version", "parent"})
        if not isinstance(data["title"], str) or not data["title"]:
            raise ValueError("design title required")
        if type(data["version"]) is not int or data["version"] < 1:
            raise ValueError("version must be a positive integer")
        if data["parent"] is not None and not isinstance(data["parent"], str):
            raise ValueError("parent must be a record reference")
        for name in ("intended_functions", "assumptions", "failure_modes", "evidence"):
            strings(data[name], name)
        for name in ("components", "relationships", "required_properties", "constraints", "construction_steps"):
            if not isinstance(data[name], list) or not all(isinstance(x, dict) for x in data[name]):
                raise ValueError(f"{name} must contain records")
        symbols = set()
        for component in data["components"]:
            keys(component, {"key", "requirements"})
            if not isinstance(component["key"], str) or component["key"] in symbols:
                raise ValueError("component keys must be unique strings")
            symbols.add(component["key"])
            if not isinstance(component["requirements"], list):
                raise ValueError("component requirements must be constraints")
            for c in component["requirements"]:
                validate_constraint(c)
        for relation in data["relationships"]:
            keys(relation, {"kind", "a", "b"})
            if relation["kind"] not in {"force", "rotation", "support", "contain"}:
                raise ValueError("unsupported relation")
            if relation["a"] not in symbols or relation["b"] not in symbols:
                raise ValueError("relationship references absent component")
        for c in data["constraints"] + data["required_properties"]:
            validate_constraint(c)
        for step in data["construction_steps"]:
            # Local symbols may be bound by a planner later; these are proposals.
            Action.from_dict(step)
            if step["kind"] not in OPERATIONS:
                raise ValueError("construction step must use a primitive operation")
            keys(step["args"], *OPERATIONS[step["kind"]])
        canonical(data)
        return cls(**deepcopy(data))


@dataclass(frozen=True)
class Idea:
    purpose: str
    assumptions: list[str]
    designs: list[str]
    evidence: list[str]
    parent: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Idea:
        keys(data, {"purpose", "assumptions", "designs", "evidence", "parent"})
        if not isinstance(data["purpose"], str) or not data["purpose"]:
            raise ValueError("idea purpose required")
        for name in ("assumptions", "designs", "evidence"):
            strings(data[name], name)
        if data["parent"] is not None and not isinstance(data["parent"], str):
            raise ValueError("idea parent must be a reference")
        return cls(**deepcopy(data))


@dataclass(frozen=True)
class Experiment:
    question: str
    constraints: list[dict]
    design: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Experiment:
        from .constraints import validate_constraint
        keys(data, {"question", "constraints", "design"})
        if not isinstance(data["question"], str) or not data["question"]:
            raise ValueError("experiment question required")
        if not isinstance(data["constraints"], list) or not data["constraints"]:
            raise ValueError("experiment requires constraints")
        if data["design"] is not None and not isinstance(data["design"], str):
            raise ValueError("design must be a record reference")
        for c in data["constraints"]:
            validate_constraint(c)
        return cls(**deepcopy(data))
