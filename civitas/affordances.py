"""Inspectable affordance descriptions backed by closed kernel operations.

Property requirements expose compatibility. Relational, epistemic and resource
preconditions are evaluated against current state on every action, never cached
as permission flags. Cost expressions below are descriptions, not executable code.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Affordance:
    name: str
    action: str
    positive_properties: tuple[str, ...]
    preconditions: tuple[str, ...]
    costs: tuple[str, ...]
    failure_codes: tuple[str, ...]

    def compatible(self, measures: dict) -> bool:
        return all(measures.get(p, 0) > 0 for p in self.positive_properties)


AFFORDANCES = (
    Affordance("observe", "observe", (), ("local visibility",), ("1 s",), ("unobservable",)),
    Affordance("move", "move", (), ("observed", "local", "supported final state", "force and power limits"),
               ("gravity and friction work in J", "requested duration in s"), ("inadequate_force", "inadequate_power", "unsupported_load")),
    Affordance("connect_force", "connect", ("tension_capacity",), ("both endpoints compatible", "within reach"),
               ("5 J effort", "1 s"), ("unsupported_connection", "unavailable_resource")),
    Affordance("connect_rotation", "connect", ("tension_capacity", "radius"), ("both endpoints compatible", "within reach"),
               ("5 J effort", "1 s"), ("unsupported_connection", "unavailable_resource")),
    Affordance("support", "connect", ("compression_capacity",), ("grounded anchor", "aggregate load within capacity", "within reach"),
               ("5 J effort", "1 s"), ("insufficient_structural_strength", "unsupported_connection")),
    Affordance("contain", "connect", ("compression_capacity",), ("aggregate volume within capacity", "aggregate load within capacity", "within reach"),
               ("5 J effort", "1 s"), ("capacity_exceeded", "insufficient_structural_strength")),
    Affordance("supply_work", "work", ("source_power",), ("connected path", "available energy", "force and power limits"),
               ("output work / path efficiency in J", "1 J effort", "requested duration in s"),
               ("unavailable_resource", "inadequate_force", "inadequate_power", "insufficient_structural_strength")),
)


def permitted(measures: dict) -> list[Affordance]:
    return [a for a in AFFORDANCES if a.compatible(measures)]


def describe(measures: dict) -> list[dict]:
    return [{k: list(v) if isinstance(v, tuple) else v for k, v in asdict(a).items()}
            for a in permitted(measures)]
