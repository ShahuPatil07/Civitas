from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from civitas.benchmarks import available, instantiate, load, outcome
from civitas.model import Action, canonical
from civitas.simulation import AgentPort, BudgetExhausted, replay, run, save
from tests.helpers import act, constraint, fixture, spec


class ReplayTests(unittest.TestCase):
    def test_same_seed_and_action_sequence_produce_identical_runs(self):
        first, second = run(spec()), run(spec())
        self.assertEqual(canonical(first), canonical(second))
        self.assertEqual(replay(first).state_hash, first["final_hash"])

    def test_serialized_runs_replay_all_four_scenarios(self):
        self.assertEqual(len(available()), 4)
        for name in available():
            with self.subTest(benchmark=name):
                record = run(load(name), 42)
                with tempfile.TemporaryDirectory() as folder:
                    path = save(record, Path(folder) / "run.json")
                    restored = json.loads(path.read_text(encoding="utf-8"))
                    self.assertEqual(replay(restored).state_hash, record["final_hash"])
                self.assertTrue(record["outcome"]["within_budget"])
                self.assertTrue(any(not e["accepted"] for e in record["events"]))

    def test_tampered_action_effect_or_digest_is_detected(self):
        record = run(spec())
        for field in ("action", "effects", "state_hash", "final_hash", "genesis", "outcome"):
            bad = deepcopy(record)
            if field == "action":
                bad["events"][0]["action"]["args"]["target"] = "missing"
            elif field == "effects":
                bad["events"][0]["effects"] = []
            elif field == "state_hash":
                bad["events"][0][field] = "tampered"
            elif field == "genesis":
                bad["genesis"]["universe"]["gravity"] = 100
            elif field == "outcome":
                bad["outcome"]["success"] = not bad["outcome"]["success"]
            else:
                bad[field] = "tampered"
            with self.subTest(field=field), self.assertRaises(ValueError):
                replay(bad)

    def test_rule_version_mismatch_fails_explicitly(self):
        record = run(spec())
        record["rule_version"] = "new-model"
        with self.assertRaisesRegex(ValueError, "version"):
            replay(record)

    def test_seed_changes_logical_world_identity(self):
        a, _ = instantiate(spec(), 42)
        b, _ = instantiate(spec(), 43)
        self.assertNotEqual(a.genesis["world_id"], b.genesis["world_id"])
        self.assertFalse(a.snapshot()["objects"].keys() & b.snapshot()["objects"].keys())

    def test_scenario_available_operations_are_enforced(self):
        config = spec()
        config["allowed_actions"] = ["observe"]
        w, task = instantiate(config)
        e = act(w, task["actor"], "believe", claim="x", value=1, confidence=1)
        self.assertFalse(e["accepted"])
        self.assertEqual(e["evaluations"][0]["code"], "unsupported_action")

    def test_experiment_budget_counts_rejected_attempts(self):
        w, task, actor, source, load_id = fixture()
        task["max_experiments"] = 1
        port = AgentPort(w, task)
        event = port.submit("experiment", {"experiment": {"question": "Unobserved?", "design": None,
                                                          "constraints": [constraint(load_id, "z", 1)]}})
        self.assertFalse(event["accepted"])
        with self.assertRaises(BudgetExhausted):
            port.submit("experiment", {})

    def test_over_budget_and_unknown_goals_cannot_pass(self):
        w, task, actor, _, load_id = fixture()
        task["goals"] = [constraint(load_id, "z", 0)]
        self.assertTrue(outcome(w, task)["success"])
        task["max_actions"] = 0
        act(w, actor, "observe", target="nearby")
        self.assertFalse(outcome(w, task)["success"])
        task["max_actions"] = 100
        task["goals"] = [constraint(load_id, "unimplemented", 0)]
        self.assertFalse(outcome(w, task)["success"])

    def test_cli_list_inspect_run_and_replay(self):
        def cli(*args):
            return subprocess.run([sys.executable, "-m", "civitas", *args], capture_output=True, text=True, check=True).stdout
        self.assertIn("mechanical", cli("benchmark", "list"))
        self.assertEqual(json.loads(cli("benchmark", "inspect", "structural"))["id"], "structural")
        with tempfile.TemporaryDirectory() as folder:
            path = str(Path(folder) / "record.json")
            self.assertIn("SUCCESS=", cli("benchmark", "run", "mechanical", "--seed", "42", "--output", path))
            self.assertIn("Replay verified", cli("replay", path))


if __name__ == "__main__":
    unittest.main()
