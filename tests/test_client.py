"""Optional graphical client checks; same kernel, no display or model required."""
import importlib.util
import os
import unittest
from unittest.mock import patch

from civitas.laboratory import Laboratory


@unittest.skipUnless(importlib.util.find_spec('pygame'), 'optional Pygame client not installed')
class ClientTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {'SDL_VIDEODRIVER': 'dummy', 'SDL_AUDIODRIVER': 'dummy', 'PYGAME_HIDE_SUPPORT_PROMPT': '1'})
        self.environment.start()
        from civitas.client import Client
        self.client = Client(Laboratory())
        self.client.draw()

    def tearDown(self):
        self.client.lab.close()
        self.client.pg.quit()
        self.environment.stop()

    def test_text_entry_creates_kernel_project_and_render_is_read_only(self):
        c, pg = self.client, self.client.pg
        c.focus = True
        c.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_RETURN, mod=0))
        self.assertIsNotNone(c.lab.project)
        self.assertEqual(c.lab.world.history[-1]['action']['kind'], 'start_project')
        c.lab.run()
        before = c.lab.world.state_hash
        for tab in ('project', 'object', 'knowledge', 'history'):
            c.perform('tab', tab)
            c.draw()
        c.debug = True
        c.draw()
        self.assertEqual(before, c.lab.world.state_hash)
        self.assertEqual(c.lab.project['status'], 'succeeded')

    def test_pause_camera_and_selection_cannot_mutate_world(self):
        c, pg = self.client, self.client.pg
        before = c.lab.world.state_hash
        c.perform('speed', 0)
        c.advance(10)
        c.handle(pg.event.Event(pg.KEYDOWN, key=pg.K_SPACE, mod=0))
        self.assertEqual(c.speed, 1)
        c.handle(pg.event.Event(pg.MOUSEWHEEL, y=1, x=0))
        self.assertGreater(c.zoom, 100)
        object_hit = next(rect for rect, identity in c.hits if identity == c.lab.target())
        c.handle(pg.event.Event(pg.MOUSEBUTTONDOWN, button=1, pos=object_hit.center))
        self.assertEqual(c.selected, c.lab.target())
        c.draw()
        self.assertEqual(before, c.lab.world.state_hash)


if __name__ == '__main__':
    unittest.main()
