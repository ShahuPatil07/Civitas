"""Bounded online composition search using only an agent port.

No world cloning, researcher evaluation, scenario names or authored graph. Trials
are real actions: accepted connections and spent resources survive failed plans.
This small policy handles one positional goal, paths up to three objects, and
one optional load-bearing relation suggested by unsupported-load feedback.
"""
from copy import deepcopy
from itertools import permutations


def _relation_key(a, b, role):
    return (role, *sorted((a, b))) if role in {"force", "rotation"} else (role, a, b)


def search(port, task):
    # Local import avoids a cycle in the run dispatcher; the port is the only
    # world capability used by this module.
    from .simulation import BudgetExhausted

    attempts, trials = 0, 0
    parent, version = None, 0
    evidence, failures = [], []
    installed = {}

    def submit(kind, args):
        nonlocal attempts
        if attempts >= task["max_actions"]:
            raise BudgetExhausted("action budget exhausted")
        attempts += 1
        return port.submit(kind, deepcopy(args))

    try:
        observation = submit("observe", {"target": "nearby"})
        if not observation["accepted"]:
            return
        evidence.append(observation["id"])
        view = port.view()
        objects = view["observations"]
        goals = [c for c in task["goals"] if c["category"] == "physical"
                 and c["measure"] in {"x", "z"} and c["op"] == ">=" and c["subject"] in objects]
        required = {"connect", "work", "record_design", "experiment"}
        if not goals or not required <= set(view["allowed_actions"]):
            return
        goal = goals[0]
        target = goal["subject"]
        axis = 0 if goal["measure"] == "x" else 1
        delta = goal["value"] - objects[target]["object"]["position"][axis]
        if delta <= 0:
            return
        dx, dz = (delta, 0) if axis == 0 else (0, delta)
        names = sorted(objects)
        capabilities = {i: {a["name"] for a in objects[i]["affordances"]} for i in names}
        sources = [i for i in names if i != target and "supply_work" in capabilities[i]]
        supports = [i for i in names if i != target and "support" in capabilities[i]]
        queue = []
        for length in (2, 3):
            for source in sources:
                others = [i for i in names if i not in {source, target}]
                for middle in permutations(others, length - 2):
                    path = [source, *middle, target]
                    for mode in ("force", "rotation"):
                        if all(f"connect_{mode}" in capabilities[i] for i in path):
                            queue.append((path, mode, None))

        while queue and trials < task["max_experiments"]:
            path, mode, support = queue.pop(0)
            relations = [{"a": a, "b": b, "kind": mode} for a, b in zip(path, path[1:])]
            if support:
                relations.append({"a": support, "b": target, "kind": "support"})
            pending = [r for r in relations if _relation_key(r["a"], r["b"], r["kind"]) not in installed]
            # Leave room for propose, construction, work, measure, and a final
            # evidence-bearing revision. Never reset an actual world to search.
            if task["max_actions"] - attempts < len(pending) + 4:
                break
            planned = list(installed.values()) + pending
            involved = sorted({i for r in planned for i in (r["a"], r["b"])} | set(path))
            motion = {"path": path, "mode": mode, "dx": dx, "dz": dz, "duration": 10}
            steps = [{"actor": task["actor"], "kind": "connect", "args": r} for r in planned]
            steps.append({"actor": task["actor"], "kind": "work", "args": motion})
            proposal = {
                "title": "Composition hypothesis", "components": [{"key": i, "requirements": []} for i in involved],
                "relationships": deepcopy(planned), "required_properties": [],
                "intended_functions": ["satisfy the measured displacement and resource constraints"],
                "constraints": deepcopy(task["goals"]), "construction_steps": steps,
                "assumptions": ["Observed properties remain applicable; the kernel must validate this plan.",
                                "Component keys bind to observed persistent identities in this world."],
                "failure_modes": sorted(set(failures)), "evidence": list(evidence),
                "parent": parent, "version": version + 1,
            }
            recorded = submit("record_design", {"design": proposal})
            if not recorded["accepted"]:
                return
            parent = recorded["metadata"]["created"]
            version += 1
            failure = None
            for r in pending:
                event = submit("connect", r)
                if not event["accepted"]:
                    failure = event["evaluations"][0]["code"]
                    break
                installed[_relation_key(r["a"], r["b"], r["kind"])] = r
                evidence.append(event["id"])
            if failure is None:
                event = submit("work", motion)
                if event["accepted"]:
                    evidence.append(event["id"])
                else:
                    failure = event["evaluations"][0]["code"]
            if failure:
                failures.append(failure)
            measurement = submit("experiment", {"experiment": {
                "question": "Does this constructed candidate satisfy all task measurements?",
                "design": parent, "constraints": task["goals"],
            }})
            trials += 1
            if not measurement["accepted"]:
                return
            evidence.append(measurement["id"])
            # Persist evidence even on failure, rather than only returning it in
            # solver memory. This revision makes no authoritative success claim.
            proposal.update(parent=parent, version=version + 1, evidence=list(evidence),
                            failure_modes=sorted(set(failures)))
            revised = submit("record_design", {"design": proposal})
            if not revised["accepted"]:
                return
            parent = revised["metadata"]["created"]
            version += 1
            if measurement["metadata"]["passed"]:
                return
            if failure == "unsupported_load" and support is None:
                queue[0:0] = [(path, mode, candidate) for candidate in supports]
    except BudgetExhausted:
        return
