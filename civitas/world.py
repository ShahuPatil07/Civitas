"""Authoritative deterministic state machine. All post-genesis writes live here."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import json
from uuid import UUID

from . import RULE_VERSION
from .affordances import describe
from .constraints import evaluate, result
from .model import OPERATIONS, Action, Design, Experiment, Idea, canonical, digest, keys, number, uid
from .physics import affordances, distance, motion_requirements, properties, relation_capacity


class Rejected(Exception):
    def __init__(self, evaluation: dict):
        self.evaluation = evaluation


def require(condition: bool, code: str, reason: str, evidence=None, blocking=None) -> None:
    if not condition:
        raise Rejected(result("unsatisfied", code, reason, evidence, blocking or [reason]))


def _diff(before: dict, after: dict) -> list[dict]:
    changes = []
    for collection in sorted(after):
        if before[collection] == after[collection]:
            continue
        if isinstance(after[collection], dict):
            for key in sorted(before[collection].keys() | after[collection].keys()):
                old, new = before[collection].get(key), after[collection].get(key)
                if old != new:
                    changes.append({"collection": collection, "id": key, "before": old, "after": new})
        else:
            changes.append({"collection": collection, "before": before[collection], "after": after[collection]})
    return deepcopy(changes)


class World:
    """Trusted researcher API. Give cognition an AgentPort, not this object."""

    def __init__(self, genesis: dict):
        self.__genesis = deepcopy(genesis)
        self.__state = deepcopy(genesis)
        self.__history: list[dict] = []
        self._validate_genesis()

    @property
    def genesis(self) -> dict:
        return deepcopy(self.__genesis)

    @property
    def history(self) -> list[dict]:
        return deepcopy(self.__history)

    @property
    def event_count(self) -> int:
        return len(self.__history)

    def snapshot(self) -> dict:
        return deepcopy(self.__state)

    @property
    def state_hash(self) -> str:
        return digest(self.__state)

    def view(self, actor: str) -> dict:
        a = self.__state["agents"][actor]
        known = {k["value"] for k in a["knowledge"] if k["origin"] == "record" and isinstance(k["value"], str)}
        return deepcopy({"id": actor, "position": a["position"], "energy": a["energy"],
                         "max_force": a["max_force"], "power": a["power"], "inventory": a["inventory"],
                         "knowledge": a["knowledge"], "observations": a["observations"],
                         "designs": {i: r for i, r in self.__state["designs"].items() if i in known},
                         "ideas": {i: r for i, r in self.__state["ideas"].items() if i in known},
                         "allowed_actions": self.__state["allowed_actions"],
                         "time": self.__state["time"]})

    def engineer_view(self, actor: str) -> dict:
        view = self.view(actor)
        view["effort_spent"] = self.__state["agents"][actor]["effort_spent"]
        view["projects"] = deepcopy({i: p for i, p in self.__state.get("projects", {}).items() if p["actor"] == actor})
        view["discoveries"] = [deepcopy(k["value"]) for k in view["knowledge"] if k["origin"] == "discovery"]
        view["materials"] = {k["claim"].split(":", 1)[1]: deepcopy(k["value"]) for k in view["knowledge"] if k["origin"] == "material_observation"}
        view["neighbors"] = {i: {"position": list(a["position"])} for i, a in self.__state["agents"].items()
                             if distance(a, self.__state["agents"][actor]) <= self.__state["universe"]["observation_radius"]}
        return view

    def evaluate(self, constraint: dict) -> dict:
        return deepcopy(evaluate(self.__state, deepcopy(constraint)))

    def _validate_genesis(self) -> None:
        s = self.__state
        keys(s, {"rule_version", "world_id", "seed", "universe", "materials", "objects", "agents",
                 "relations", "designs", "ideas", "experiments", "time", "allowed_actions"}, {"projects"})
        if s["rule_version"] not in {RULE_VERSION, "civitas-semantic-0.2"}:
            raise ValueError("incompatible rule version")
        if s.get("projects"):
            raise ValueError("genesis must not contain projects; load through replay")
        if s['rule_version'] == 'civitas-semantic-0.2' and not isinstance(s.get('projects'), dict):
            raise ValueError('0.2 genesis requires an empty projects mapping')
        UUID(s["world_id"])
        if type(s["seed"]) is not int or s["time"] != 0:
            raise ValueError("genesis requires integer seed and zero time")
        if not isinstance(s["allowed_actions"], list) or not set(s["allowed_actions"]) <= OPERATIONS.keys():
            raise ValueError("unknown permitted operation")
        u = s["universe"]
        keys(u, {"gravity", "observation_radius", "transfer_efficiency"})
        number(u["gravity"], "gravity", 0)
        number(u["observation_radius"], "observation radius", 0)
        efficiency = number(u["transfer_efficiency"], "transfer efficiency", 0.001)
        if efficiency > 1:
            raise ValueError("efficiency must not exceed one")
        ids = set()
        for collection in ("materials", "objects", "agents", "relations", "designs", "ideas", "experiments"):
            if not isinstance(s[collection], dict):
                raise ValueError(f"{collection} must be a mapping")
            for identity in s[collection]:
                UUID(identity)
                if identity in ids:
                    raise ValueError("duplicate persistent identity")
                ids.add(identity)
        for m in s["materials"].values():
            keys(m, {"label", "density", "tensile_strength", "compressive_strength", "friction", "shape_energy"})
            if not isinstance(m["label"], str):
                raise ValueError("material label must be text")
            for name in m.keys() - {"label"}:
                number(m[name], name, 1e-9 if name == "density" else 0)
        for obj in s["objects"].values():
            keys(obj, {"material", "mass", "length", "radius", "position", "angle", "environment_work", "human_work", "motions"}, {"source"})
            if obj["material"] not in s["materials"]:
                raise ValueError("missing object material")
            for name in ("mass", "length", "radius"):
                number(obj[name], name, 1e-9 if name != "radius" else 0)
            self._position(obj["position"])
            if obj["position"][1] != 0 or any(obj[k] != 0 for k in ("angle", "environment_work", "human_work")) or obj["motions"]:
                raise ValueError("genesis objects must start grounded with no historical work")
            if "source" in obj:
                keys(obj["source"], {"energy", "power", "max_force"})
                for name, value in obj["source"].items():
                    number(value, name, 0)
        for a in s["agents"].values():
            keys(a, {"position", "energy", "power", "max_force", "effort_spent", "inventory", "knowledge", "observations"})
            self._position(a["position"])
            if a["position"][1] != 0 or a["effort_spent"] != 0 or a["observations"]:
                raise ValueError("agents start grounded, with no effort or implicit observations")
            for name in ("energy", "power", "max_force"):
                number(a[name], name, 0)
            for m, quantity in a["inventory"].items():
                if m not in s["materials"]:
                    raise ValueError("unknown inventory material")
                number(quantity, "stock mass", 0)
            if not isinstance(a["knowledge"], list):
                raise ValueError("knowledge must be a list")
            for claim in a["knowledge"]:
                keys(claim, {"claim", "value", "confidence", "evidence", "origin"})
                if claim["origin"] != "initial" or not isinstance(claim["claim"], str):
                    raise ValueError("initial claim has invalid origin")
                if not 0 <= number(claim["confidence"], "confidence") <= 1:
                    raise ValueError("invalid initial confidence")
                if claim["evidence"]:
                    raise ValueError("genesis claims cannot cite nonexistent events")
        if any(s[k] for k in ("relations", "designs", "ideas", "experiments")):
            raise ValueError("v0 genesis starts without assembled relations or research records")
        canonical(s)

    @staticmethod
    def _position(position) -> None:
        if not isinstance(position, list) or len(position) != 2:
            raise ValueError("position must be [x, z]")
        number(position[0], "x")
        number(position[1], "z", 0)

    def submit(self, action: Action) -> dict:
        """An attempt always produces an audit event; physical changes are atomic."""
        # Non-JSON input is outside the protocol, rather than a replayable action.
        # Normalize Python tuples and JSON object keys before validation so disk
        # replay cannot interpret the same serialized request differently.
        data = json.loads(canonical(action.to_dict()))
        event_id = uid(self.__state["world_id"], f"event/{len(self.__history)}")
        staged = deepcopy(self.__state)
        evaluations = []
        metadata = {}
        try:
            action = Action.from_dict(data)
            require(action.actor in staged["agents"], "unknown_actor", "Actor is unavailable")
            require(action.kind in OPERATIONS and action.kind in staged["allowed_actions"],
                    "unsupported_action", "Operation is not available")
            keys(data["args"], *OPERATIONS[action.kind])
            metadata, evaluations = self._dispatch(staged, data, event_id)
            self._physical_invariants(staged)
            canonical(staged)
            evaluations.insert(0, result("satisfied", "action_valid", "Action preconditions and postconditions hold"))
            accepted = True
        except Rejected as error:
            evaluations = [error.evaluation]
            accepted = False
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            evaluations = [result("unsatisfied", "invalid_schema", str(error), blocking=["Supply valid structured arguments"])]
            accepted = False
        effects = _diff(self.__state, staged) if accepted else []
        if accepted:
            self.__state = staged
        event = {"id": event_id, "sequence": len(self.__history), "action": data,
                 "accepted": accepted, "evaluations": evaluations, "effects": effects,
                 "metadata": metadata if accepted else {}, "state_hash": self.state_hash}
        self.__history.append(deepcopy(event))
        return deepcopy(event)

    def _known_object(self, s: dict, actor: str, target: str, local: bool = True) -> dict:
        a = s["agents"][actor]
        require(isinstance(target, str) and target in a["observations"], "insufficient_knowledge", "An observation of the target is required")
        obj = s["objects"][target]
        if local:
            require(distance(a, obj) <= s["universe"]["observation_radius"], "out_of_reach", "Target is outside the interaction radius")
        return obj

    @staticmethod
    def _charge(s: dict, actor: str, energy: float, duration: float) -> None:
        a = s["agents"][actor]
        require(a["energy"] >= energy, "unavailable_resource", "Insufficient effort energy", {"available_J": a["energy"], "required_J": energy})
        a["energy"] -= energy
        a["effort_spent"] += energy
        s["time"] += duration

    @staticmethod
    def _claim(s: dict, actor: str, claim: str, value, event_id: str, origin: str, confidence: float = 1) -> None:
        s["agents"][actor]["knowledge"].append({"claim": claim, "value": deepcopy(value), "confidence": confidence,
                                               "evidence": [event_id], "origin": origin})

    def _observe(self, s: dict, actor: str, target: str, event_id: str) -> dict:
        # Unavailable and distant identities intentionally have the same feedback.
        require(target in s["objects"] and distance(s["agents"][actor], s["objects"][target]) <= s["universe"]["observation_radius"],
                "unobservable", "Target is not locally observable")
        obj = s["objects"][target]
        observation = {"object": deepcopy(obj), "properties": properties(obj, s["materials"]),
                       "material": deepcopy(s["materials"][obj["material"]]),
                       "affordances": describe(properties(obj, s["materials"])), "time": s["time"], "evidence": event_id}
        s["agents"][actor]["observations"][target] = observation
        self._claim(s, actor, f"observed:{target}", observation, event_id, "observation")
        return observation

    def _dispatch(self, s: dict, data: dict, event_id: str) -> tuple[dict, list]:
        actor, kind, args = data["actor"], data["kind"], data["args"]
        a = s["agents"][actor]
        metadata, evaluations = {}, []
        if kind in {"start_project", "reason_project", "step_project", "stop_project"}:
            from .projects import dispatch
            return dispatch(self, s, data, event_id)
        if kind == "inspect_resources":
            for material in sorted(a["inventory"]):
                self._claim(s, actor, f"material:{material}", s["materials"][material], event_id, "material_observation")
            self._charge(s, actor, 0, 1)
            return {"message": "Material stocks inspected"}, []
        if kind == "disconnect":
            identity = args["relation"]
            require(identity in s["relations"], "unknown_relation", "Relation is unavailable")
            r = s["relations"][identity]
            self._known_object(s, actor, r["a"])
            self._known_object(s, actor, r["b"])
            del s["relations"][identity]
            self._charge(s, actor, 2, 1)
            self._claim(s, actor, f"removed_relation:{identity}", r, event_id, "construction")
            return {"removed": identity}, []
        if kind == "observe":
            require(isinstance(args["target"], str), "invalid_schema", "target must be an identity or nearby")
            targets = sorted(s["objects"]) if args["target"] == "nearby" else [args["target"]]
            if args["target"] == "nearby":
                targets = [t for t in targets if distance(a, s["objects"][t]) <= s["universe"]["observation_radius"]]
            for target in targets:
                self._observe(s, actor, target, event_id)
            self._charge(s, actor, 0, 1)
            metadata = {"observed": targets}
        elif kind == "shape":
            m = args["material"]
            require(isinstance(m, str) and m in a["inventory"], "unavailable_resource", "Material stock is unavailable")
            mass = number(args["mass"], "mass", 1e-6)
            length = number(args["length"], "length", 1e-6)
            radius = number(args["radius"], "radius", 0)
            require(any(k["claim"] == f"shape:{m}" and k["origin"] in {"initial", "experiment"} and k["value"] is True for k in a["knowledge"]),
                    "insufficient_knowledge", "Material shaping capability is not known")
            require(a["inventory"][m] >= mass, "unavailable_resource", "Insufficient stock mass", {"available_kg": a["inventory"][m], "required_kg": mass})
            energy = mass * s["materials"][m]["shape_energy"]
            require(a["power"] > 0 or energy == 0, "inadequate_power", "Shaping needs effort power")
            self._charge(s, actor, energy, max(1, energy / max(a["power"], 1e-9)))
            a["inventory"][m] -= mass
            identity = uid(s["world_id"], f"{event_id}/object")
            s["objects"][identity] = {"material": m, "mass": mass, "length": length, "radius": radius,
                                       "position": list(a["position"]), "angle": 0, "environment_work": 0,
                                       "human_work": 0, "motions": []}
            self._observe(s, actor, identity, event_id)
            metadata = {"created": identity, "energy_J": energy}
        elif kind == "connect":
            left, right, role = args["a"], args["b"], args["kind"]
            x = self._known_object(s, actor, left)
            y = self._known_object(s, actor, right)
            require(role in {"force", "rotation", "support", "contain"}, "unsupported_connection", "Relation kind is not modeled")
            require(left != right, "unsupported_connection", "An object cannot connect to itself")
            require(not any({r["a"], r["b"]} == {left, right} and r["kind"] == role for r in s["relations"].values()),
                    "duplicate_connection", "This relation already exists")
            need = {"force": "connect_force", "rotation": "connect_rotation", "support": "support", "contain": "contain"}[role]
            require(need in affordances(x, s["materials"]) and (role in {"support", "contain"} or need in affordances(y, s["materials"])),
                    "unsupported_connection", "Properties do not expose the requested affordance")
            if role in {"support", "contain"}:
                require(not any(r["b"] == right and r["kind"] in {"support", "contain"} for r in s["relations"].values()),
                        "unsupported_connection", "v0 permits one support or container per load")
                require(not any(r["b"] == left and r["kind"] in {"support", "contain"} for r in s["relations"].values()),
                        "unsupported_connection", "Nested load-bearing relations are not modeled")
                require(not any(r["a"] == right and r["kind"] in {"support", "contain"} for r in s["relations"].values()),
                        "unsupported_connection", "Nested load-bearing relations are not modeled")
            relation_id = uid(s["world_id"], f"{event_id}/relation")
            s["relations"][relation_id] = {"a": left, "b": right, "kind": role,
                                           "span": abs(x["position"][0] - y["position"][0])}
            self._charge(s, actor, 5, 1)
            self._claim(s, actor, f"relation:{relation_id}", s["relations"][relation_id], event_id, "construction")
            metadata = {"created": relation_id}
        elif kind in {"move", "work"}:
            metadata = self._motion(s, actor, kind, args)
            self._observe(s, actor, metadata["target"], event_id)
            if s['rule_version'] == 'civitas-semantic-0.2' and kind == 'work':
                for identity in args['path'][:-1]:
                    self._observe(s, actor, identity, event_id)
        elif kind in {"record_design", "record_idea"}:
            design = kind == "record_design"
            proposal = args["design" if design else "idea"]
            record = Design.from_dict(proposal) if design else Idea.from_dict(proposal)
            collection = "designs" if design else "ideas"
            known_records = {k["value"] for k in a["knowledge"] if k["origin"] == "record" and isinstance(k["value"], str)}
            if record.parent:
                require(record.parent in known_records and record.parent in s[collection], "insufficient_knowledge", "Parent record is not known")
            if design:
                require((not record.parent and record.version == 1) or (record.parent and record.version == s[collection][record.parent]["content"]["version"] + 1),
                        "invalid_lineage", "Design version must follow its parent")
            else:
                require(all(d in known_records and d in s["designs"] for d in record.designs), "insufficient_knowledge", "Associated designs must be known")
            known_evidence = {e for k in a["knowledge"] for e in k["evidence"]}
            require(set(record.evidence) <= known_evidence, "insufficient_knowledge", "Evidence must have been observed by this agent")
            identity = uid(s["world_id"], f"{event_id}/{collection}")
            s[collection][identity] = {"author": actor, "content": asdict(record)}
            self._claim(s, actor, f"{collection}:{identity}", identity, event_id, "record")
            self._charge(s, actor, 0, 1)
            metadata = {"created": identity, "hypothesis_only": True}
        elif kind == "believe":
            require(isinstance(args["claim"], str), "invalid_schema", "claim must be text")
            confidence = number(args["confidence"], "confidence", 0)
            require(confidence <= 1, "invalid_schema", "confidence must be <= 1")
            canonical(args["value"])
            self._claim(s, actor, args["claim"], args["value"], event_id, "assertion", confidence)
            self._charge(s, actor, 0, 1)
        elif kind == "experiment":
            experiment = Experiment.from_dict(args["experiment"])
            if s['rule_version'] == 'civitas-semantic-0.2':
                self._charge(s, actor, 1, 1)
            if experiment.design:
                require(experiment.design in s["designs"] and any(k["value"] == experiment.design and k["origin"] == "record" for k in a["knowledge"]),
                        "insufficient_knowledge", "Experiment design must be known")
            for c in experiment.constraints:
                if c["subject"] in s["objects"]:
                    self._known_object(s, actor, c["subject"])
                else:
                    require(c["subject"] == actor, "unobservable", "Experiment subject is not observable")
                evaluations.append(evaluate(s, c))
            identity = uid(s["world_id"], f"{event_id}/experiment")
            outcome = all(r["status"] == "satisfied" for r in evaluations)
            s["experiments"][identity] = {"author": actor, "proposal": asdict(experiment), "results": deepcopy(evaluations), "passed": outcome}
            self._claim(s, actor, f"experiment:{identity}", s["experiments"][identity], event_id, "experiment")
            if s['rule_version'] != 'civitas-semantic-0.2':
                self._charge(s, actor, 1, 1)
            metadata = {"created": identity, "passed": outcome}
        return metadata, evaluations

    def _motion(self, s: dict, actor: str, kind: str, args: dict) -> dict:
        dx, dz = number(args["dx"], "dx"), number(args["dz"], "dz")
        duration = number(args["duration"], "duration", 1e-6)
        require(dx != 0 or dz != 0, "no_motion", "Motion requires a nonzero displacement")
        path = args["path"] if kind == "work" else [args["target"]]
        require(isinstance(path, list) and 1 <= len(path) <= 16 and all(isinstance(p, str) for p in path), "invalid_schema", "Path must contain 1–16 identities")
        require(len(set(path)) == len(path), "unsupported_connection", "Transmission path cannot repeat nodes")
        nodes = [self._known_object(s, actor, p) for p in path]
        target = nodes[-1]
        require("source" not in target, "anchored_source", "Environmental boundary conditions are anchored")
        require(not any(r["a"] == path[-1] and r["kind"] in {"support", "contain"} for r in s["relations"].values()),
                "unsupported_motion", "Movement of loaded supports/containers is not modeled")
        req = motion_requirements(target, dx, dz, s["materials"], s["universe"]["gravity"])
        a = s["agents"][actor]
        efficiency, input_energy, mode = 1.0, req["work"], "human"
        if kind == "move":
            require(req["force"] <= a["max_force"], "inadequate_force", "Agent force is insufficient", {"required_N": req["force"], "available_N": a["max_force"]})
            require(input_energy <= a["power"] * duration, "inadequate_power", "Agent power is insufficient for this duration")
            self._charge(s, actor, input_energy, duration)
            target["human_work"] += req["work"]
        else:
            require(len(path) >= 2 and "source" in nodes[0], "unavailable_resource", "Work requires an environmental source and connected target")
            mode = args.get("mode", "force")
            require(mode in {"force", "rotation"}, "unsupported_connection", "Transmission mode must be force or rotation")
            edges = []
            for left, right in zip(path, path[1:]):
                candidates = [r for _, r in sorted(s["relations"].items()) if {r["a"], r["b"]} == {left, right} and r["kind"] == mode]
                require(bool(candidates), "unsupported_connection", "A path segment cannot transfer motion")
                edges.append(candidates[0])
            efficiency = s["universe"]["transfer_efficiency"] ** len(edges)
            ratio = nodes[0]["radius"] / target["radius"] if mode == "rotation" else 1
            source = nodes[0]["source"]
            available = source["max_force"] * ratio * efficiency
            require(req["force"] <= available, "inadequate_force", "Transmitted force is insufficient", {"required_N": req["force"], "available_N": available})
            for i, edge in enumerate(edges):
                capacity = relation_capacity(nodes[i], nodes[i + 1], mode, s["materials"])
                demand = req["force"] * (target["radius"] if mode == "rotation" else 1) / s["universe"]["transfer_efficiency"] ** (len(edges) - i)
                require(demand <= capacity, "insufficient_structural_strength", "Transmission exceeds connection capacity", {"required": demand, "capacity": capacity, "unit": "Nm" if mode == "rotation" else "N"})
            input_energy = req["work"] / efficiency
            require(input_energy <= source["energy"], "unavailable_resource", "Environmental energy reservoir is insufficient", {"required_J": input_energy, "available_J": source["energy"]})
            require(input_energy <= source["power"] * duration, "inadequate_power", "Environmental power is insufficient for this duration")
            source["energy"] -= input_energy
            target["environment_work"] += req["work"]
            if mode == "rotation":
                angle = req["distance"] / target["radius"]
                for obj in nodes:
                    obj["angle"] += angle
            self._charge(s, actor, 1, duration)
        old = list(target["position"])
        target["position"] = [old[0] + dx, old[1] + dz]
        target["motions"].append({"from": old, "to": list(target["position"]), "mode": mode,
                                   "output_J": req["work"], "input_J": input_energy})
        return {"target": path[-1], "motion": deepcopy(target["motions"][-1]), "efficiency": efficiency}

    def _physical_invariants(self, s: dict) -> None:
        objects, mats, gravity = s["objects"], s["materials"], s["universe"]["gravity"]
        loads = {}
        for r in s["relations"].values():
            a, b = objects[r["a"]], objects[r["b"]]
            reach = a["length"] if r["kind"] in {"support", "contain"} else a["length"] + b["length"]
            require(distance(a, b) <= reach, "unsupported_connection", "Connection endpoints exceed available reach", {"distance_m": distance(a, b), "reach_m": reach})
            r["span"] = abs(a["position"][0] - b["position"][0])
            if r["kind"] in {"support", "contain"}:
                require(a["position"][1] == 0, "unsupported_connection", "v0 load-bearing anchors must be grounded")
                capacity = relation_capacity(a, b, r["kind"], mats, r["span"])
                demand = b["mass"] * gravity
                loads.setdefault(r["a"], []).append((demand, capacity))
                if r["kind"] == "contain":
                    used = sum(properties(objects[q["b"]], mats)["volume"] for q in s["relations"].values() if q["kind"] == "contain" and q["a"] == r["a"])
                    require(used <= properties(a, mats)["volume"], "capacity_exceeded", "Containment volume is insufficient")
        for entries in loads.values():
            demand, capacity = sum(x[0] for x in entries), min(x[1] for x in entries)
            require(demand <= capacity, "insufficient_structural_strength", "Aggregate supported load exceeds structural capacity", {"required_N": demand, "capacity_N": capacity})
        for identity, obj in objects.items():
            self._position(obj["position"])
            if obj["position"][1] > 0:
                require(any(r["b"] == identity and r["kind"] in {"support", "contain"} for r in s["relations"].values()),
                        "unsupported_load", "An elevated object needs a load-bearing relation")
