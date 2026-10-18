from copy import deepcopy
import unittest

from civitas.benchmarks import outcome
from civitas.materials import catalog
from civitas.physics import affordances, properties
from tests.helpers import act, constraint, fixture, material, spec


class PhysicsTests(unittest.TestCase):
    def setUp(self):
        self.w, self.task, self.actor, self.source, self.load = fixture()
        act(self.w, self.actor, "observe", target="nearby")

    def shape(self, mass=2, length=3, radius=.4):
        e = act(self.w, self.actor, "shape", material=material(self.w, "wood"), mass=mass, length=length, radius=radius)
        self.assertTrue(e["accepted"], e)
        return e["metadata"]["created"]

    def connect(self, a, b, role):
        e = act(self.w, self.actor, "connect", a=a, b=b, kind=role)
        self.assertTrue(e["accepted"], e)
        return e

    def test_assembled_unnamed_components_produce_useful_behavior(self):
        # No artifact type or recipe: a newly shaped segment gains behavior by
        # composition with two distinct relation roles and a boundary condition.
        middle = self.shape()
        self.connect(self.source, middle, "force")
        self.connect(middle, self.load, "force")
        self.connect(middle, self.load, "support")
        before = self.w.snapshot()["objects"][self.source]["source"]["energy"]
        e = act(self.w, self.actor, "work", path=[self.source, middle, self.load], dx=0, dz=1, duration=2)
        self.assertTrue(e["accepted"], e)
        state = self.w.snapshot()
        load = state["objects"][self.load]
        self.assertEqual(load["position"], [1, 1])
        self.assertAlmostEqual(load["environment_work"], 98.1)
        self.assertEqual(load["human_work"], 0)
        self.assertAlmostEqual(before - state["objects"][self.source]["source"]["energy"], 98.1 / .81)
        self.assertEqual(load["motions"][0]["mode"], "force")
        self.assertNotIn("type", state["objects"][middle])

    def test_rotational_transmission_accounts_for_angle_and_losses(self):
        self.connect(self.source, self.load, "rotation")
        self.connect(self.source, self.load, "force")
        before = self.w.snapshot()["objects"][self.source]["source"]["energy"]
        e = act(self.w, self.actor, "work", path=[self.source, self.load], mode="rotation", dx=1, dz=0, duration=1)
        self.assertTrue(e["accepted"], e)
        state = self.w.snapshot()
        self.assertAlmostEqual(state["objects"][self.source]["angle"], 2)
        self.assertAlmostEqual(state["objects"][self.load]["angle"], 2)
        expected = 10 * 9.81 * .7
        self.assertAlmostEqual(before - state["objects"][self.source]["source"]["energy"], expected / .9)

    def test_force_power_and_energy_are_distinct_constraints(self):
        for field, value, expected in (("max_force", 1, "inadequate_force"), ("power", 1, "inadequate_power"), ("energy", 1, "unavailable_resource")):
            config = spec()
            config["objects"]["boundary"]["source"][field] = value
            w, _, actor, source, load = fixture(config)
            act(w, actor, "observe", target="nearby")
            act(w, actor, "connect", a=source, b=load, kind="force")
            before = w.state_hash
            e = act(w, actor, "work", path=[source, load], dx=1, dz=0, duration=1)
            self.assertFalse(e["accepted"])
            self.assertEqual(e["evaluations"][0]["code"], expected)
            self.assertEqual(w.state_hash, before)

    def test_overloaded_connection_and_aggregate_support_are_rejected(self):
        thin = self.shape(mass=.001, length=3)
        before = self.w.state_hash
        e = act(self.w, self.actor, "connect", a=thin, b=self.load, kind="support")
        self.assertEqual(e["evaluations"][0]["code"], "insufficient_structural_strength")
        self.assertEqual(before, self.w.state_hash)
        support = self.shape(mass=.008, length=3)
        self.connect(support, self.load, "support")
        # Individually each load fits; their total does not.
        config = spec()
        config["objects"]["another"] = deepcopy(config["objects"]["load"])
        w, _, actor, _, load = fixture(config)
        act(w, actor, "observe", target="nearby")
        support = act(w, actor, "shape", material=material(w, "wood"), mass=.008, length=3, radius=.4)["metadata"]["created"]
        first = act(w, actor, "connect", a=support, b=load, kind="support")
        self.assertTrue(first["accepted"])
        other = next(i for i, o in w.snapshot()["objects"].items() if o["mass"] == 10 and i != load)
        e = act(w, actor, "connect", a=support, b=other, kind="support")
        self.assertEqual(e["evaluations"][0]["code"], "insufficient_structural_strength")

    def test_transmission_strength_is_checked_under_load(self):
        thin = self.shape(mass=.0001, length=2)
        self.connect(self.source, thin, "force")
        self.connect(thin, self.load, "force")
        e = act(self.w, self.actor, "work", path=[self.source, thin, self.load], dx=1, dz=0, duration=1)
        self.assertFalse(e["accepted"])
        self.assertEqual(e["evaluations"][0]["code"], "insufficient_structural_strength")

    def test_friction_and_gravity_change_measured_cost(self):
        e = act(self.w, self.actor, "move", target=self.load, dx=1, dz=0, duration=1)
        self.assertTrue(e["accepted"])
        self.assertAlmostEqual(e["metadata"]["motion"]["input_J"], 68.67)
        config = spec()
        config["universe"]["gravity"] = 2
        w, _, actor, _, load = fixture(config)
        act(w, actor, "observe", target="nearby")
        e = act(w, actor, "move", target=load, dx=1, dz=0, duration=1)
        self.assertAlmostEqual(e["metadata"]["motion"]["input_J"], 14)

    def test_altered_gravity_changes_feasibility(self):
        outcomes = []
        for gravity in (2, 9.81):
            config = spec()
            config["universe"]["gravity"] = gravity
            config["agent"]["max_force"] = 30
            w, _, actor, source, load = fixture(config)
            act(w, actor, "observe", target="nearby")
            act(w, actor, "connect", a=source, b=load, kind="support")
            e = act(w, actor, "move", target=load, dx=0, dz=1, duration=1)
            outcomes.append(e["accepted"])
        self.assertEqual(outcomes, [True, False])

    def test_material_labels_do_not_control_physics(self):
        state = self.w.snapshot()
        mats = state["materials"]
        obj = state["objects"][self.load]
        expected = (properties(obj, mats), affordances(obj, mats))
        for m in mats.values():
            m["label"] = "anonymous substrate"
        self.assertEqual(expected, (properties(obj, mats), affordances(obj, mats)))
        self.assertEqual(len(catalog()), 10)

    def test_containment_uses_aggregate_volume(self):
        small = self.shape(mass=.01)
        e = act(self.w, self.actor, "connect", a=small, b=self.load, kind="contain")
        self.assertEqual(e["evaluations"][0]["code"], "capacity_exceeded")

    def test_long_connections_and_underground_motion_are_atomic_failures(self):
        self.connect(self.source, self.load, "force")
        before = self.w.state_hash
        for dx, dz in ((100, 0), (0, -1)):
            e = act(self.w, self.actor, "move", target=self.load, dx=dx, dz=dz, duration=100)
            self.assertFalse(e["accepted"])
            self.assertEqual(self.w.state_hash, before)

    def test_repeated_crossings_cannot_be_faked_with_small_upward_steps(self):
        self.connect(self.source, self.load, "support")
        c = constraint(self.load, "crossings", 2, lower=0, upper=1)
        for dz in (.5, .5, .1):
            self.assertTrue(act(self.w, self.actor, "move", target=self.load, dx=0, dz=dz, duration=1)["accepted"])
        self.assertEqual(self.w.evaluate(c)["evidence"]["actual"], 1)
        self.assertTrue(act(self.w, self.actor, "move", target=self.load, dx=0, dz=-1.1, duration=1)["accepted"])
        self.assertTrue(act(self.w, self.actor, "move", target=self.load, dx=0, dz=1, duration=1)["accepted"])
        self.assertEqual(self.w.evaluate(c)["status"], "satisfied")

    def test_goal_recognizes_distinct_primitive_action_solutions(self):
        # Calibration only, not a solution to the four research scenarios.
        self.assertFalse(outcome(self.w, self.task)["success"])
        act(self.w, self.actor, "move", target=self.load, dx=1, dz=0, duration=1)
        self.assertTrue(outcome(self.w, self.task)["success"])
        w, task, actor, source, load = fixture()
        act(w, actor, "observe", target="nearby")
        act(w, actor, "connect", a=source, b=load, kind="force")
        act(w, actor, "work", path=[source, load], dx=1, dz=0, duration=1)
        self.assertTrue(outcome(w, task)["success"])


if __name__ == "__main__":
    unittest.main()
