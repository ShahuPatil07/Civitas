"""Kernel-owned project transitions; called only from World's staged dispatcher."""
from copy import deepcopy
from .cognition import validate_proposal, validate_physical_action
from .constraints import evaluate, result
from .model import canonical, keys, uid

TERMINAL = {"succeeded", "unresolved", "exhausted"}
PROJECT_RULE_VERSION = "civitas-semantic-0.2"


def dispatch(kernel, s, data, event_id):
    from .world import Rejected, require
    actor, args, kind = data["actor"], data["args"], data["kind"]
    require(s["rule_version"] == PROJECT_RULE_VERSION, "unsupported_action", "Project actions require a 0.2 world")
    if kind == "start_project":
        require(isinstance(args["text"], str) and 0 < len(args["text"]) <= 4000, "invalid_schema", "Goal text must contain 1–4000 characters")
        keys(args["budgets"], {"actions", "experiments", "reasoning"})
        for value in args["budgets"].values():
            require(type(value) is int and 1 <= value <= 500, "invalid_schema", "Budgets must be integers in 1–500")
        require(type(args["use_knowledge"]) is bool, "invalid_schema", "use_knowledge must be boolean")
        if args["target"] is not None:
            kernel._known_object(s, actor, args["target"])
        require(not any(p["actor"] == actor and p["status"] not in TERMINAL for p in s.get("projects", {}).values()), "active_project", "Finish the current project first")
        identity = uid(s["world_id"], f"{event_id}/project")
        s.setdefault("projects", {})[identity] = {
            "id": identity, "actor": actor, "text": args["text"], "target": args["target"],
            "budgets": deepcopy(args["budgets"]), "counts": {"actions": 0, "experiments": 0, "reasoning": 0},
            "use_knowledge": args["use_knowledge"], "goals": [], "status": "interpreting", "feasibility": "unknown",
            "artifacts": [], "attempts": [], "designs": [], "experiments": [], "queue": [], "active_design": None,
            "latest": None, "started": s["time"], "initial_effort": s["agents"][actor]["effort_spent"],
            "pending_experiment": False, "usage": {"input_tokens": 0, "output_tokens": 0, "cost": 0},
        }
        kernel._charge(s, actor, 0, 1)
        return {"created": identity, "message": "Goal received"}, []
    p = s.get("projects", {}).get(args["project"])
    require(p is not None and p["actor"] == actor, "unknown_project", "Project is not known to this actor")
    require(p["status"] not in TERMINAL, "closed_project", "Project is already closed")
    if kind == "reason_project":
        require(not p["queue"] and not p["pending_experiment"], "plan_pending", "Execute the recorded plan first")
        require(p["counts"]["reasoning"] < p["budgets"]["reasoning"], "budget_exhausted", "Reasoning budget exhausted")
        artifact = validate_proposal(args["proposal"])
        keys(args["usage"], {"input_tokens", "output_tokens", "cost"})
        require(all(type(args["usage"][k]) is int and args["usage"][k] >= 0 for k in ("input_tokens", "output_tokens"))
                and args["usage"]["cost"] == 0, "invalid_schema", "Only zero-cost providers are enabled")
        for k, v in args["usage"].items():
            p["usage"][k] += v
        p["counts"]["reasoning"] += 1
        p["artifacts"].append({**artifact, "event": event_id})
        ak, payload = artifact["kind"], artifact["payload"]
        if ak == "intent":
            require(not p["goals"], "frozen_goal", "Project goals cannot be overwritten")
            for c in payload["goals"]:
                require(c["subject"] == actor or c["subject"] in s["agents"][actor]["observations"], "insufficient_knowledge", "Goal subject must be known")
            p["goals"], p["status"] = deepcopy(payload["goals"]), "planning"
        elif ak in {"candidate_design", "design_revision"}:
            require(bool(p["goals"]), "missing_goal", "Interpret the goal first")
            design = payload["design"]
            require(all(step["actor"] == actor for step in design["construction_steps"]), "invalid_actor", "Plan may act only as its owner")
            meta, _ = kernel._dispatch(s, {"actor": actor, "kind": "record_design", "args": {"design": design}}, event_id)
            p["active_design"] = meta["created"]
            p["designs"].append(meta["created"])
            p["queue"] = deepcopy(design["construction_steps"])
            p["pending_experiment"], p["status"] = True, "constructing"
        elif ak in {"plan", "action_proposal"}:
            require(bool(p["goals"]), "missing_goal", "Interpret the goal first")
            require(all(a["actor"] == actor for a in payload["actions"]), "invalid_actor", "Plan may act only as its owner")
            p["queue"], p["status"] = deepcopy(payload["actions"]), "acting"
        elif ak == "experiment_proposal":
            require(bool(p["goals"]), "missing_goal", "Interpret the goal first")
            p["pending_experiment"] = True
        elif ak == "unresolved":
            p["status"], p["feasibility"] = "unresolved", "unknown"
        kernel._charge(s, actor, 0, 1)
        return {"project": p["id"], "artifact": ak, "summary": artifact["summary"]}, []
    if kind == "stop_project":
        require(isinstance(args["reason"], str) and len(args["reason"]) <= 1000, "invalid_schema", "Invalid stop reason")
        p["status"] = "exhausted" if any(p["counts"][k] >= p["budgets"][k] for k in p["counts"]) else "unresolved"
        p["latest"], p["queue"], p["pending_experiment"] = {"code": "stopped", "reason": args["reason"]}, [], False
        kernel._charge(s, actor, 0, 1)
        return {"project": p["id"], "message": args["reason"]}, []
    require(kind == "step_project", "unsupported_action", "Unsupported project transition")
    require(p["counts"]["actions"] < p["budgets"]["actions"], "budget_exhausted", "Action budget exhausted")
    p["counts"]["actions"] += 1
    if p["queue"]:
        operation = p["queue"].pop(0)
        validate_physical_action(operation)
        require(operation["kind"] in s["allowed_actions"], "unsupported_action", "Physical operation is unavailable")
        trial = deepcopy(s)
        try:
            meta, checks = kernel._dispatch(trial, operation, event_id)
            kernel._physical_invariants(trial)
            canonical(trial)
            s.clear()
            s.update(trial)
            p = s["projects"][p["id"]]
            accepted = True
        except Rejected as error:
            meta, checks, accepted = {}, [error.evaluation], False
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            meta, checks, accepted = {}, [result("unsatisfied", "invalid_schema", str(error))], False
        entry = {"action": operation, "accepted": accepted, "evaluations": checks, "metadata": meta, "event": event_id}
        p["attempts"].append(entry)
        p["latest"] = entry
        if not accepted:
            p["queue"], p["pending_experiment"], p["status"] = [], bool(p["active_design"]), "diagnosing"
            kernel._claim(s, actor, f"failure:{event_id}", entry, event_id, "observation")
        return {"project": p["id"], "operation": operation, "operation_accepted": accepted, **meta}, checks
    require(p["pending_experiment"] and bool(p["goals"]), "nothing_pending", "No action or experiment is queued")
    require(p["counts"]["experiments"] < p["budgets"]["experiments"], "budget_exhausted", "Experiment budget exhausted")
    meta, _ = kernel._dispatch(s, {"actor": actor, "kind": "experiment", "args": {"experiment": {
        "question": p["text"], "constraints": p["goals"], "design": p["active_design"]}}}, event_id)
    p["counts"]["experiments"] += 1
    p["experiments"].append(meta["created"])
    p["pending_experiment"] = False
    checks = [evaluate(s, c) for c in p["goals"]]
    passed = all(c["status"] == "satisfied" for c in checks)
    p["latest"] = {"experiment": meta["created"], "passed": passed, "evaluations": checks, "event": event_id}
    p["status"] = "succeeded" if passed else "diagnosing"
    p["feasibility"] = "known_feasible" if passed else "currently_unrealizable"
    if passed and p["active_design"]:
        design = s["designs"][p["active_design"]]["content"]
        paths = [a["args"] for a in design["construction_steps"] if a["kind"] == "work"]
        discovery = {"design": p["active_design"], "project": p["id"], "experiment": meta["created"], "demonstrated": checks,
            "principles": [{"kind": "measured_transfer", "path": a["path"], "mode": a.get("mode", "force"),
                            "gravity": s["universe"]["gravity"]} for a in paths[:1]],
            "scope": "Measured in this world; reuse requires another experiment."}
        kernel._claim(s, actor, f"discovery:{p['id']}", discovery, event_id, "discovery")
    elif not passed and set(s["objects"]) <= s["agents"][actor]["observations"].keys():
        for c in p["goals"]:
            if c["category"] == "physical" and c["measure"] == "environment_work" and c["op"] == ">=":
                bound = s["objects"][c["subject"]]["environment_work"] + sum(o.get("source", {}).get("energy", 0) for o in s["objects"].values())
                if bound < c["value"]:
                    p["feasibility"], p["status"] = "known_infeasible", "unresolved"
                    p["latest"]["certificate"] = {"code": "energy_upper_bound", "available_J": bound, "required_J": c["value"]}
    return {"project": p["id"], "experiment": meta["created"], "passed": passed, "feasibility": p["feasibility"]}, checks
