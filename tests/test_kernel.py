from copy import deepcopy
import json
import unittest
from uuid import UUID

from civitas.benchmarks import instantiate, outcome
from civitas.model import Action, Design
from civitas.simulation import AgentPort, BudgetExhausted
from civitas.world import World
from tests.helpers import act, constraint, design, fixture, material, spec


class KernelTests(unittest.TestCase):
    def setUp(self):
        self.w, self.task, self.actor, self.source, self.load = fixture()

    def observe(self):
        return act(self.w, self.actor, "observe", target="nearby")

    def assertRejected(self, event, code):
        self.assertFalse(event["accepted"], event)
        self.assertEqual(event["evaluations"][0]["code"], code)
        self.assertEqual(event["effects"], [])

    def test_no_public_mutable_state_references(self):
        genesis = self.w.genesis
        genesis["agents"][self.actor]["energy"] = 1e12
        snapshot = self.w.snapshot()
        snapshot["objects"][self.load]["position"][0] = 99
        before = self.w.state_hash
        self.observe()
        current = self.w.state_hash
        view = self.w.view(self.actor)
        view["observations"][self.load]["object"]["position"][0] = 999
        history = self.w.history
        history[0]["effects"].clear()
        self.assertEqual(self.w.state_hash, current)
        self.assertNotEqual(current, before)
        self.assertEqual(self.w.snapshot()["objects"][self.load]["position"], [1, 0])
        self.assertTrue(self.w.history[0]["effects"])

    def test_unobserved_target_and_self_asserted_observation(self):
        act(self.w, self.actor, "believe", claim=f"observed:{self.load}", value=True, confidence=1)
        event = act(self.w, self.actor, "move", target=self.load, dx=1, dz=0, duration=1)
        self.assertRejected(event, "insufficient_knowledge")

    def test_rejection_atomic_even_after_staged_resource_charge(self):
        self.observe()
        before = self.w.snapshot()
        event = act(self.w, self.actor, "move", target=self.load, dx=0, dz=1, duration=1)
        self.assertRejected(event, "unsupported_load")
        self.assertEqual(before, self.w.snapshot())
        self.assertEqual(len(self.w.history), 2)

    def test_closed_schema_and_no_state_patch_action(self):
        before = self.w.state_hash
        event = act(self.w, self.actor, "set_position", target=self.load, position=[0, 99])
        self.assertRejected(event, "unsupported_action")
        event = act(self.w, self.actor, "observe", target="nearby", energy=1e12)
        self.assertRejected(event, "invalid_schema")
        self.assertEqual(before, self.w.state_hash)

    def test_invalid_numerics_are_not_committed(self):
        self.observe()
        for dx in ("1", True, None):
            event = act(self.w, self.actor, "move", target=self.load, dx=dx, dz=0, duration=1)
            self.assertRejected(event, "invalid_schema")
        before = self.w.state_hash
        for dx in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                act(self.w, self.actor, "move", target=self.load, dx=dx, dz=0, duration=1)
        self.assertEqual(before, self.w.state_hash)

    def test_genesis_validates_invariants_and_versions(self):
        for field, value in (("rule_version", "future"), ("time", 1)):
            g = self.w.genesis
            g[field] = value
            with self.assertRaises(ValueError):
                World(g)
        g = self.w.genesis
        g["objects"][self.load]["position"][1] = 1
        with self.assertRaises(ValueError):
            World(g)
        g = self.w.genesis
        g["agents"][self.actor]["inventory"][material(self.w, "wood")] = -1
        with self.assertRaises(ValueError):
            World(g)

    def test_unknown_and_distant_observation_do_not_disclose_truth(self):
        config = spec()
        config["objects"]["load"]["position"] = [100, 0]
        w, _, actor, _, load = fixture(config)
        a = act(w, actor, "observe", target=load)
        b = act(w, actor, "observe", target="missing")
        self.assertEqual(a["evaluations"], b["evaluations"])
        act(w, actor, "observe", target="nearby")
        self.assertNotIn(load, w.view(actor)["observations"])

    def test_agent_knowledge_is_separate_and_can_be_false(self):
        other = next(i for i in self.w.snapshot()["agents"] if i != self.actor)
        self.observe()
        self.assertFalse(self.w.view(other)["observations"])
        act(self.w, self.actor, "believe", claim="load_mass", value=9999, confidence=.7)
        act(self.w, self.actor, "believe", claim="load_mass", value=1, confidence=.3)
        self.assertEqual(self.w.snapshot()["objects"][self.load]["mass"], 10)
        self.assertEqual(len([k for k in self.w.view(self.actor)["knowledge"] if k["claim"] == "load_mass"]), 2)
        self.assertFalse(self.w.view(other)["knowledge"])

    def test_self_assertion_cannot_grant_manufacturing_capability(self):
        config = spec()
        config["agent"]["known_shaping"] = []
        w, _, actor, _, _ = fixture(config)
        m = material(w, "wood")
        act(w, actor, "believe", claim=f"shape:{m}", value=True, confidence=1)
        self.assertRejected(act(w, actor, "shape", material=m, mass=1, length=1, radius=.2), "insufficient_knowledge")

    def test_stock_mass_and_effort_are_conserved(self):
        m = material(self.w, "wood")
        event = act(self.w, self.actor, "shape", material=m, mass=2, length=3, radius=.2)
        self.assertTrue(event["accepted"])
        state = self.w.snapshot()
        self.assertEqual(state["agents"][self.actor]["inventory"][m], 8)
        self.assertEqual(state["objects"][event["metadata"]["created"]]["mass"], 2)
        self.assertEqual(state["agents"][self.actor]["effort_spent"], 40)
        before = self.w.state_hash
        self.assertRejected(act(self.w, self.actor, "shape", material=m, mass=100, length=1, radius=.1), "unavailable_resource")
        self.assertEqual(before, self.w.state_hash)

    def test_property_based_affordance_rejects_zero_strength(self):
        self.observe()
        event = act(self.w, self.actor, "shape", material=material(self.w, "water"), mass=1, length=1, radius=.2)
        obj = event["metadata"]["created"]
        self.assertRejected(act(self.w, self.actor, "connect", a=obj, b=self.load, kind="force"), "unsupported_connection")
        observed = self.w.view(self.actor)["observations"][obj]
        self.assertNotIn("connect_force", [a["name"] for a in observed["affordances"]])

    def test_design_roundtrip_and_hypothesis_does_not_grant_success(self):
        proposal = design()
        model = Design.from_dict(json.loads(json.dumps(proposal)))
        self.assertEqual(model.to_dict(), proposal)
        before = self.w.snapshot()["objects"]
        event = act(self.w, self.actor, "record_design", design=proposal)
        self.assertTrue(event["accepted"])
        identity = event["metadata"]["created"]
        self.assertEqual(self.w.view(self.actor)["designs"][identity]["content"], proposal)
        other = next(i for i in self.w.snapshot()["agents"] if i != self.actor)
        self.assertNotIn(identity, self.w.view(other)["designs"])
        self.assertEqual(self.w.snapshot()["objects"], before)
        self.assertFalse(outcome(self.w, self.task)["success"])
        child = deepcopy(proposal)
        child.update(parent=identity, version=2)
        self.assertTrue(act(self.w, self.actor, "record_design", design=child)["accepted"])
        child["version"] = 9
        self.assertRejected(act(self.w, self.actor, "record_design", design=child), "invalid_lineage")

    def test_design_schema_and_forged_evidence_rejected(self):
        proposal = design()
        proposal["relationships"][0]["b"] = "absent"
        self.assertRejected(act(self.w, self.actor, "record_design", design=proposal), "invalid_schema")
        proposal = design()
        proposal["evidence"] = ["invented-proof"]
        self.assertRejected(act(self.w, self.actor, "record_design", design=proposal), "insufficient_knowledge")
        proposal = design()
        proposal["construction_steps"] = [{"actor": self.actor, "kind": "set_state", "args": {}}]
        self.assertRejected(act(self.w, self.actor, "record_design", design=proposal), "invalid_schema")

    def test_idea_persistence_references_known_design(self):
        d = act(self.w, self.actor, "record_design", design=design())["metadata"]["created"]
        proposal = {"purpose": "Transmit a measured load", "assumptions": [], "designs": [d], "evidence": [], "parent": None}
        event = act(self.w, self.actor, "record_idea", idea=proposal)
        self.assertTrue(event["accepted"])
        self.assertEqual(self.w.snapshot()["ideas"][event["metadata"]["created"]]["content"], proposal)

    def test_failed_experiment_is_valid_action_and_persists_evidence(self):
        self.observe()
        event = act(self.w, self.actor, "experiment", experiment={"question": "Is the load elevated?", "design": None,
                                                                 "constraints": [constraint(self.load, "z", 1)]})
        self.assertTrue(event["accepted"])
        self.assertFalse(event["metadata"]["passed"])
        self.assertEqual(event["evaluations"][1]["status"], "unsatisfied")
        knowledge = self.w.view(self.actor)["knowledge"][-1]
        self.assertEqual(knowledge["origin"], "experiment")
        self.assertEqual(knowledge["evidence"], [event["id"]])

    def test_experiment_cannot_read_other_agents_private_resources(self):
        other = next(i for i in self.w.snapshot()["agents"] if i != self.actor)
        e = act(self.w, self.actor, "experiment", experiment={"question": "How much energy?", "design": None,
                                                           "constraints": [constraint(other, "energy", 1, "resource")]})
        self.assertRejected(e, "unobservable")

    def test_unknown_constraint_is_not_satisfied(self):
        for category in ("economic", "social", "institutional", "manufacturing"):
            r = self.w.evaluate(constraint(self.load, "capacity", 1, category))
            self.assertEqual(r["status"], "unknown")
            self.assertTrue(r["blocking_requirements"])
        self.assertEqual(self.w.evaluate(constraint(self.load, "unmodeled", 0))["status"], "unknown")

    def test_knowledge_constraint_and_resource_measurement(self):
        c = constraint(self.actor, "known", 1, "knowledge", claim="new claim")
        self.assertEqual(self.w.evaluate(c)["status"], "unsatisfied")
        act(self.w, self.actor, "believe", claim="new claim", value=False, confidence=.4)
        # 'known' means a claim is held; it does not assert the claim is true.
        self.assertEqual(self.w.evaluate(c)["status"], "satisfied")
        self.assertEqual(self.w.evaluate(constraint(self.actor, "energy", 10000, "resource"))["status"], "satisfied")
        m = material(self.w, "wood")
        self.assertEqual(self.w.evaluate(constraint(self.actor, "stock_mass", 11, "resource", material=m))["status"], "unsatisfied")

    def test_python_inputs_are_normalized_to_the_json_protocol(self):
        # A tuple would otherwise reject in memory but become a valid list on disk.
        self.observe()
        act(self.w, self.actor, "connect", a=self.source, b=self.load, kind="force")
        e = act(self.w, self.actor, "work", path=(self.source, self.load), dx=1, dz=0, duration=1)
        self.assertTrue(e["accepted"])
        self.assertIsInstance(e["action"]["args"]["path"], list)
        reconstructed = World(self.w.genesis)
        for expected in json.loads(json.dumps(self.w.history)):
            self.assertEqual(reconstructed.submit(Action.from_dict(expected["action"])), expected)

    def test_budget_and_port_do_not_disclose_effects(self):
        task = deepcopy(self.task)
        task["max_actions"] = 1
        port = AgentPort(self.w, task)
        event = port.submit("observe", {"target": "nearby"})
        self.assertNotIn("effects", event)
        self.assertNotIn("state_hash", event)
        self.assertNotIn("agents", port.view())
        with self.assertRaises(BudgetExhausted):
            port.submit("observe", {"target": "nearby"})
        self.assertEqual(len(self.w.history), 1)

    def test_persistent_ids_and_rejections_have_causal_history(self):
        first = self.observe()
        rejected = act(self.w, self.actor, "unknown")
        self.assertEqual(rejected["sequence"], 1)
        self.assertEqual(rejected["action"]["kind"], "unknown")
        for i in (self.actor, self.source, self.load, first["id"], rejected["id"]):
            UUID(i)
        self.assertEqual(len({self.actor, self.source, self.load, first["id"], rejected["id"]}), 5)


if __name__ == "__main__":
    unittest.main()
