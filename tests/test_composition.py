from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from benchmarks.composition.run import scenarios
from civitas.benchmarks import instantiate, load, outcome
from civitas.composition import search
from civitas.materials import catalog
from civitas.simulation import AgentPort, replay, run


class CompositionTests(unittest.TestCase):
    def test_feasible_composition_uses_three_bodies_and_persists_evidence(self):
        record = run(scenarios()["feasible"], solver="composition")
        self.assertTrue(record["outcome"]["success"])
        world = replay(record)
        state = world.snapshot()
        self.assertEqual(len(state["objects"]), 3)
        motions = [e for e in record["events"] if e["accepted"] and e["action"]["kind"] == "work"]
        self.assertEqual(len(motions), 1)
        self.assertEqual(len(motions[0]["action"]["args"]["path"]), 3)
        self.assertAlmostEqual(motions[0]["metadata"]["motion"]["output_J"], 98.1)
        self.assertAlmostEqual(motions[0]["metadata"]["motion"]["input_J"], 98.1 / .81)
        rejected = [e["evaluations"][0]["code"] for e in record["events"] if not e["accepted"]]
        self.assertIn("unsupported_load", rejected)
        self.assertIn("unsupported_connection", rejected)
        versions = sorted(state["designs"].items(), key=lambda pair: pair[1]["content"]["version"])
        for n, (identity, design) in enumerate(versions):
            self.assertEqual(design["content"]["version"], n + 1)
            self.assertEqual(design["content"]["parent"], versions[n - 1][0] if n else None)
        measured = [e for e in record["events"] if e["action"]["kind"] == "experiment"]
        self.assertTrue(measured[-1]["metadata"]["passed"])
        self.assertIn(measured[-1]["id"], versions[-1][1]["content"]["evidence"])
        # The measured proposal exists before its construction/work, and its
        # exact proposed motion is the one actually submitted to the kernel.
        tested = state["experiments"][measured[-1]["metadata"]["created"]]["proposal"]["design"]
        steps = state["designs"][tested]["content"]["construction_steps"]
        self.assertEqual(steps[-1], motions[-1]["action"])
        other = next(i for i in state["agents"] if i != record["task"]["actor"])
        self.assertFalse(world.view(other)["designs"])

    def test_insufficient_energy_control_cannot_manufacture_success(self):
        record = run(scenarios()["insufficient_energy"], solver="composition")
        self.assertFalse(record["outcome"]["success"])
        state = replay(record).snapshot()
        self.assertTrue(all(not e["passed"] for e in state["experiments"].values()))
        target = record["task"]["goals"][0]["subject"]
        self.assertEqual(state["objects"][target]["position"][1], 0)
        self.assertEqual(state["objects"][target]["environment_work"], 0)
        source = next(o for o in state["objects"].values() if "source" in o)
        self.assertEqual(source["source"]["energy"], 50)
        codes = [e["evaluations"][0]["code"] for e in record["events"] if not e["accepted"]]
        self.assertIn("unavailable_resource", codes)

    def test_same_policy_transfers_to_changed_gravity(self):
        record = run(scenarios()["gravity_transfer"], solver="composition")
        self.assertTrue(record["outcome"]["success"])
        target = record["task"]["goals"][0]["subject"]
        state = replay(record).snapshot()
        self.assertAlmostEqual(state["objects"][target]["environment_work"], 120)

    def test_complete_json_replay_and_determinism(self):
        for name, spec in scenarios().items():
            with self.subTest(case=name):
                record = run(spec, solver="composition")
                self.assertEqual(record, run(spec, solver="composition"))
                self.assertEqual(replay(json.loads(json.dumps(record))).state_hash, record["final_hash"])

    def test_labels_and_scenario_names_do_not_encode_the_solution(self):
        spec = scenarios()["feasible"]
        spec["id"] = "unrelated-label"
        spec["description"] = "Only numeric goals are supplied."
        materials = catalog()
        ids = {m["label"]: i for i, m in materials.items()}
        for n, material in enumerate(materials.values()):
            material["label"] = f"anonymous-{n}"
        spec["materials"] = materials
        for obj in spec["objects"].values():
            obj["material"] = ids[obj["material"]]
        spec["objects"] = {"renamed-" + k: v for k, v in spec["objects"].items()}
        for goal in spec["goals"]:
            if goal["subject"] != "agent":
                goal["subject"] = "renamed-" + goal["subject"]
        self.assertTrue(run(spec, solver="composition")["outcome"]["success"])

    def test_solver_needs_only_observation_and_submission_port(self):
        world, task = instantiate(scenarios()["feasible"])
        real = AgentPort(world, task)
        port = SimpleNamespace(view=real.view, submit=real.submit)
        task.pop("id")
        task.pop("description")
        search(port, task)
        self.assertTrue(outcome(world, task)["success"])

    def test_small_action_and_experiment_budgets_are_respected(self):
        for limit in (0, 1, 4, 10):
            spec = scenarios()["feasible"]
            spec["max_actions"] = limit
            spec["max_experiments"] = 1
            record = run(spec, solver="composition")
            self.assertTrue(record["outcome"]["within_budget"])
            self.assertLessEqual(record["outcome"]["attempts"], limit)
            self.assertFalse(record["outcome"]["success"])

    def test_existing_reference_runs_remain_identical(self):
        path = Path(__file__).resolve().parents[1] / "benchmarks/results/baseline-42-summary.json"
        for reference in json.loads(path.read_text(encoding="utf-8")):
            record = run(load(reference["benchmark"]), 42)
            self.assertEqual(record["final_hash"], reference["final_hash"])

    def test_unknown_solver_does_not_silently_run_baseline(self):
        with self.assertRaisesRegex(ValueError, "unknown solver"):
            run(scenarios()["feasible"], solver="missing")


if __name__ == "__main__":
    unittest.main()
