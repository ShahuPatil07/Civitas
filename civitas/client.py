"""Replaceable Pygame view. Physics and cognition live outside this module."""
from math import cos, sin
from pathlib import Path
import textwrap

from .laboratory import Laboratory, DEFAULT_GOAL
from .planner import relations
from .projects import TERMINAL
from .replies import plan_lines, reply


class Client:
    def __init__(self, lab, save_path='runs/laboratory.json'):
        import pygame
        self.pg = pygame
        pygame.init()
        self.screen = pygame.display.set_mode((1360, 880), pygame.RESIZABLE)
        pygame.display.set_caption('CIVITAS | Experimental world')
        self.font = pygame.font.SysFont('consolas', 16)
        self.small = pygame.font.SysFont('consolas', 14)
        self.title = pygame.font.SysFont('segoeui', 25, bold=True)
        self.lab, self.save_path = lab, save_path
        self.zoom, self.pan = 100.0, [240.0, 0.0]
        self.speed, self.last_speed, self.credit = 1, 1, 0.0
        self.debug, self.pause_experiment, self.focus = False, False, False
        self.selected, self.target = lab.actor, lab.target()
        self.text = DEFAULT_GOAL
        self.notice = 'Select a load, then tell the Engineer what to attempt.'
        self.tab, self.scroll, self.event_scroll = 'project', 0, 0
        self.buttons, self.hits = [], []
        self.drag = None
        self.project_selected = None
        self.cache_count, self.view, self.history = -1, {}, []
        self.update_cache()

    def update_cache(self):
        # The kernel is not copied every rendering frame.
        count = self.lab.world.event_count
        if count != self.cache_count:
            self.view = self.lab.view
            self.history = self.lab.world.history
            self.cache_count = count

    def label(self, text, pos, color=(207, 219, 231), font=None):
        self.screen.blit((font or self.font).render(str(text), True, color), pos)

    def button(self, text, rect, action, active=False):
        pg = self.pg
        r = pg.Rect(rect)
        pg.draw.rect(self.screen, (43, 94, 98) if active else (37, 48, 63), r, border_radius=5)
        self.label(text, (r.x + 9, r.y + 7), font=self.small)
        self.buttons.append((r, action))

    def point(self, position):
        return (int(self.canvas.x + self.pan[0] + position[0] * self.zoom),
                int(self.canvas.bottom - 130 + self.pan[1] - position[1] * self.zoom))

    def wrap(self, lines, width):
        result = []
        for line in lines:
            result.extend(textwrap.wrap(str(line), width=max(15, width), break_long_words=True) or [''])
        return result

    def panel_lines(self):
        v = self.view
        project = v['projects'].get(self.project_selected or self.lab.project_id)
        if self.tab == 'history':
            lines = ['PROJECT HISTORY', 'Press [ / ] to select a project.']
            for identity, p in v['projects'].items():
                lines += [f'{">" if project and project["id"] == identity else " "} {identity[:8]} {p["status"]}: {p["text"]}']
            if project:
                lines += ['', 'ARTIFACTS / DESIGN LINEAGE']
                for a in project['artifacts']:
                    lines += [a['kind'] + ': ' + a['summary']]
                    if 'design' in a['payload']:
                        d = a['payload']['design']
                        lines += [f'v{d["version"]}, parent {str(d["parent"])[:8]}, {len(d["evidence"])} evidence references']
                lines += ['', 'EXPERIMENT RESULTS']
                for k in v['knowledge']:
                    if k['origin'] == 'experiment' and k['claim'].split(':', 1)[1] in project['experiments']:
                        lines += [k['claim'][:30]] + [r['reason'] for r in k['value']['results']]
            return lines
        if self.tab == 'knowledge':
            lines = ['ENGINEER KNOWLEDGE', f'{len(v["knowledge"])} claims / {len(v["discoveries"])} discoveries', '', 'KNOWN MATERIAL STOCK']
            for identity, mass in v['inventory'].items():
                m = v['materials'].get(identity, {})
                lines += [f'{m.get("label", identity[:8])}: {mass:g} kg; tensile {m.get("tensile_strength", 0):g} Pa']
            for d in v['discoveries']:
                lines += ['', 'MEASURED DISCOVERY ' + d['design'][:8], d['scope'], 'Evidence: ' + d['experiment'][:8]]
                lines += [f'{p["kind"]}: {p["mode"]}; {len(p["path"])} bodies; g={p["gravity"]:g}' for p in d['principles']]
            lines += ['', 'RECENT CLAIMS'] + [f'{k["origin"]}: {k["claim"]}' for k in v['knowledge'][-20:]]
            return lines
        if self.tab == 'object':
            if self.selected in v['observations']:
                o = v['observations'][self.selected]
                lines = ['OBSERVED OBJECT ' + self.selected[:8], f'Observed at t={o["time"]:g}s', f'Material: {o["material"]["label"]}', 'PROPERTIES']
                lines += [f'{k}: {value:g}' for k, value in o['properties'].items()]
                lines += ['AFFORDANCES'] + [a['name'] for a in o['affordances']]
                lines += ['MOTION EVIDENCE'] + [str(m) for m in o['object']['motions'][-4:]]
                return lines
            if self.selected != self.lab.actor:
                return ['OBSERVER ' + self.selected[:8], 'Visible position only.', 'This agent has no autonomous policy yet.', 'Private knowledge is not disclosed.']
        lines = ['ENGINEER ' + self.lab.actor[:8], f'Known energy: {v["energy"]:g} J', f'Target: {self.target[:8]}', '']
        language = self.lab.translator.name if self.lab.translator else 'grammar only (no network)'
        lines += ['Language: ' + language, '']
        if self.lab.pending_task:
            lines += ['READING YOUR REQUEST', self.lab.pending_task[0], 'Translating into checked steps...', '']
        lines += plan_lines(self.lab.agenda, v['projects'])
        lines += ['', 'CURRENT PROJECT'] if self.lab.agenda else ['CURRENT PROJECT']
        if not project:
            return lines + ['No active project.', 'Click the command field below.', 'Enter submits your goal.']
        said = reply(project, self.lab.last_error if project['id'] == self.lab.project_id else None)
        lines += [project['text'], '', f'ENGINEER SAYS [{said["category"]}]', said['headline']]
        lines += [said['detail'], ''] if said['detail'] and said['category'] != 'in_progress' else ['']
        lines += [f'{project["status"].upper()} / {project["feasibility"]}',
                  f'Actions {project["counts"]["actions"]}/{project["budgets"]["actions"]} | tests {project["counts"]["experiments"]}/{project["budgets"]["experiments"]}',
                  f'Reasoning {project["counts"]["reasoning"]}/{project["budgets"]["reasoning"]}; cost $0', '']
        next_action = project['queue'][0]['kind'] if project['queue'] else 'experiment' if project['pending_experiment'] else 'reasoning' if project['status'] not in TERMINAL else 'none'
        lines += [f'Next action: {next_action} | design v{len(project["designs"])}']
        blockers = [r['reason'] for r in (project['latest'] or {}).get('evaluations', []) if r['status'] != 'satisfied']
        if blockers:
            lines += ['Blocker: ' + blockers[0]]
        if self.lab.pending:
            lines += ['Waiting for local reasoning...']
        lines += ['']
        for kind, heading in [('intent', 'INTERPRETED GOAL'), ('hypothesis', 'HYPOTHESIS'), ('diagnosis', 'LATEST DIAGNOSIS')]:
            a = next((a for a in reversed(project['artifacts']) if a['kind'] == kind), None)
            if a:
                lines += [heading, a['summary'], '']
        design = v['designs'].get(project['active_design'])
        if design:
            d = design['content']
            lines += [f'DESIGN v{d["version"]} / {project["active_design"][:8]}', f'{len(d["components"])} components, {len(d["relationships"])} relations', f'Parent: {str(d["parent"])[:8]}', '']
        lines += ['PLAN / NEXT ACTION']
        lines += [str(a['kind']) + ': ' + str(a['args']) for a in project['queue'][:3]] or ['No construction action queued.']
        if self.lab.pending:
            lines += ['Waiting for local reasoning...']
        latest = project['latest'] or {}
        lines += ['', 'LATEST OBSERVATION'] + [r['reason'] for r in latest.get('evaluations', [])]
        if latest.get('certificate'):
            lines += [str(latest['certificate'])]
        if self.lab.last_error:
            lines += [self.lab.last_error]
        return lines

    def draw(self):
        pg = self.pg
        self.update_cache()
        w, h = self.screen.get_size()
        self.buttons, self.hits = [], []
        sidebar = min(430, int(w * .36))
        self.canvas = pg.Rect(18, 112, w - sidebar - 44, h - 338)
        self.input_rect = pg.Rect(18, h - 67, w - 36, 45)
        self.panel = pg.Rect(w - sidebar - 12, 112, sidebar, h - 338)
        self.screen.fill((16, 23, 33))
        self.label('CIVITAS', (22, 15), (107, 225, 191), self.title)
        self.label('A world of hypotheses', (155, 23), (134, 155, 176), self.small)
        self.label(f't = {self.view["time"]:g}s', (385, 23))
        for i, speed in enumerate((0, 1, 5, 20)):
            self.button('Pause' if speed == 0 else f'{speed}x', (530 + i * 70, 13, 64, 32), ('speed', speed), self.speed == speed)
        self.button('Save F5', (830, 13, 90, 32), ('save', None))
        self.button('Load F9', (930, 13, 90, 32), ('load', None))
        self.button('Debug F3', (1030, 13, 100, 32), ('debug', None), self.debug)
        language = self.lab.translator.name if self.lab.translator else 'grammar only'
        self.label(f'Planner: {self.lab.provider.name}  |  Language: {language}', (22, 59), (221, 185, 112), self.small)
        self.label('Pan: right drag / arrows   Zoom: wheel   Step: N   Pause on test: P   Inspect: tabs', (22, 84), font=self.small)
        pg.draw.rect(self.screen, (22, 35, 46), self.canvas, border_radius=8)
        self.screen.set_clip(self.canvas)
        ground = self.point([0, 0])[1]
        pg.draw.rect(self.screen, (39, 52, 44), (self.canvas.x, ground + 18, self.canvas.width, self.canvas.height))
        for x in range(-20, 30):
            point = self.point([x, 0])
            pg.draw.line(self.screen, (36, 49, 61), (point[0], self.canvas.y), (point[0], ground + 18))
            self.label(f'{x}m', (point[0] - 8, ground + 25), (103, 129, 139), self.small)
        for z in range(1, 10):
            y = self.point([0, z])[1]
            pg.draw.line(self.screen, (33, 46, 58), (self.canvas.x, y), (self.canvas.right, y))
            self.label(f'{z}m', (self.canvas.x + 5, y - 15), (103, 129, 139), self.small)
        observed = self.view['observations']
        # Construction-area marking describes owned stock; it is not another entity.
        workshop = self.point(self.view['position'])
        self.label('STOCK / CONSTRUCTION', (workshop[0] - 90, ground + 52), (164, 192, 156), self.small)
        colors = {'force': (232, 178, 93), 'rotation': (184, 150, 238), 'support': (94, 209, 167), 'contain': (119, 175, 223)}
        for r in relations(self.view).values():
            if r['a'] in observed and r['b'] in observed:
                a, b = self.point(observed[r['a']]['object']['position']), self.point(observed[r['b']]['object']['position'])
                pg.draw.line(self.screen, colors[r['kind']], a, b, 4 if r['kind'] == 'support' else 2)
                self.label(r['kind'], ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2 - 20), colors[r['kind']], self.small)
        p = self.view['projects'].get(self.project_selected or self.lab.project_id)
        if p and p['active_design']:
            d = self.view['designs'][p['active_design']]['content']
            # Proposed graph is a dotted overlay, visibly distinguished from construction.
            for r in d['relationships']:
                if r['a'] in observed and r['b'] in observed:
                    a, b = self.point(observed[r['a']]['object']['position']), self.point(observed[r['b']]['object']['position'])
                    for i in range(0, 20, 2):
                        pg.draw.line(self.screen, (87, 105, 126), (a[0] + (b[0] - a[0]) * i / 20, a[1] + (b[1] - a[1]) * i / 20 - 8),
                                     (a[0] + (b[0] - a[0]) * (i + 1) / 20, a[1] + (b[1] - a[1]) * (i + 1) / 20 - 8), 1)
        body_label_index = 0
        for identity, observation in observed.items():
            o = observation['object']
            x, y = self.point(o['position'])
            source = 'source' in o
            color = (89, 192, 226) if source else (191, 155, 108) if o['length'] > 1 else (171, 180, 190)
            size = 14 if source else max(8, min(23, o['mass'] ** (1 / 3) * 5))
            pg.draw.circle(self.screen, color, (x, y), int(size))
            if o['length'] > 1:
                end = (int(x + cos(o['angle']) * o['length'] * self.zoom / 2), int(y - sin(o['angle']) * o['length'] * self.zoom / 2))
                pg.draw.line(self.screen, color, (x, y), end, 7)
            pg.draw.line(self.screen, (24, 35, 44), (x, y), (x + cos(o['angle']) * size, y - sin(o['angle']) * size), 3)
            if identity == self.target:
                pg.draw.circle(self.screen, (241, 212, 126), (x, y), int(size + 5), 2)
            label = f'{o["source"]["energy"]:.0f} J' if source else f'{o["mass"]:g} kg / {identity[:4]}'
            self.label(label, (x - 40, y - 100 if source else y - 43 - (body_label_index % 2) * 20), color, self.small)
            if not source:
                body_label_index += 1
            if source:
                self.label('MECHANICAL SOURCE', (x - 72, y - 120), color, self.small)
            self.hits.append((pg.Rect(x - 25, y - 30, 50, 55), identity))
        for identity, neighbor in self.view['neighbors'].items():
            x, y = self.point(neighbor['position'])
            y += 65
            engineer = identity == self.lab.actor
            color = (110, 231, 187) if engineer else (136, 157, 187)
            pg.draw.circle(self.screen, color, (x, y - 9), 6)
            pg.draw.rect(self.screen, color, (x - 7, y, 14, 17), border_radius=3)
            self.label('Engineer' if engineer else 'Observer', (x - 30, y + 21), color, self.small)
            self.hits.append((pg.Rect(x - 22, y - 20, 44, 40), identity))
        self.label('Solid: built relations   Dotted: design proposal   Positions are discrete observations', (self.canvas.x + 10, self.canvas.y + 10), (149, 171, 188), self.small)
        self.screen.set_clip(None)
        pg.draw.rect(self.screen, (26, 35, 48), self.panel, border_radius=8)
        for i, tab in enumerate(('project', 'object', 'knowledge', 'history')):
            self.button(tab.title(), (self.panel.x + 6 + i * (sidebar - 12) / 4, self.panel.y + 7, (sidebar - 18) / 4, 30), ('tab', tab), self.tab == tab)
        lines = self.wrap(self.panel_lines(), (sidebar - 30) // 8)
        self.screen.set_clip(pg.Rect(self.panel.x + 10, self.panel.y + 45, sidebar - 20, self.panel.height - 50))
        for i, line in enumerate(lines[self.scroll:]):
            self.label(line, (self.panel.x + 12, self.panel.y + 50 + i * 19), font=self.small)
        self.screen.set_clip(None)
        event_y = h - 213
        self.label('WORLD EVENTS', (22, event_y), (107, 225, 191), self.small)
        self.label('Scroll this feed for older events; scroll the side panel for full details.', (170, event_y), (132, 152, 171), self.small)
        events = self.history[max(0, len(self.history) - 5 - self.event_scroll):len(self.history) - self.event_scroll if self.event_scroll else None]
        for i, e in enumerate(events):
            meta = e['metadata']
            failed = not e['accepted'] or meta.get('operation_accepted') is False or meta.get('passed') is False
            message = meta.get('summary') or meta.get('message') or meta.get('operation', {}).get('kind') or e['action']['kind']
            reasons = [r['reason'] for r in e['evaluations'] if r['status'] != 'satisfied']
            if reasons:
                message += ' | ' + reasons[0]
            if 'passed' in meta:
                message += ' | TEST ' + ('PASSED' if meta['passed'] else 'FAILED')
            self.label(f'{e["sequence"]:03d}  {message}'[:(w - 40) // 8], (22, event_y + 22 + i * 18), (239, 155, 137) if failed else (178, 198, 214), self.small)
        self.label(self.notice[:(w - 40) // 8], (22, h - 89), (219, 195, 142), self.small)
        pg.draw.rect(self.screen, (30, 47, 59), self.input_rect, border_radius=6)
        pg.draw.rect(self.screen, (100, 214, 179) if self.focus else (67, 85, 104), self.input_rect, 2, border_radius=6)
        visible = self.text[-max(10, (w - 70) // 9):]
        self.label(visible + ('|' if self.focus else ''), (30, h - 54))
        if self.debug:
            s = self.lab.world.snapshot()
            lines = ['DEBUG / WORLD TRUTH', f'seed {s["seed"]} | g={s["universe"]["gravity"]}', f'events {len(self.history)} | hash {self.lab.world.state_hash[:16]}',
                     f'objects {len(s["objects"])} | relations {len(s["relations"])}', f'Pause on experiment: {self.pause_experiment}', 'N: one controller step; P: toggle test pause']
            if self.selected in s['objects']:
                lines += [f'ID {self.selected}', str(s['objects'][self.selected])]
            overlay = pg.Rect(28, 152, min(600, self.canvas.width - 20), 150)
            pg.draw.rect(self.screen, (12, 18, 27), overlay)
            for i, line in enumerate(self.wrap(lines, overlay.width // 8)[:7]):
                self.label(line, (overlay.x + 8, overlay.y + 8 + 18 * i), (234, 188, 111), self.small)
        pg.display.flip()

    def perform(self, action, value=None):
        if action == 'speed':
            self.speed = value
            if value:
                self.last_speed = value
        elif action == 'tab':
            self.tab, self.scroll = value, 0
        elif action == 'debug':
            self.debug = not self.debug
        elif action == 'save':
            self.lab.save(self.save_path)
            self.notice = 'Saved world, knowledge, projects and event history: ' + str(self.save_path)
        elif action == 'load':
            try:
                restored = Laboratory.load(self.save_path, self.lab.provider)
                self.lab.close()
                self.lab = restored
                self.cache_count = -1
                self.project_selected = None
                self.selected, self.target = restored.actor, restored.target()
                self.notice = 'Replay verified. World restored.'
            except (OSError, ValueError, KeyError) as error:
                self.notice = 'Load failed: ' + str(error)
        elif action == 'submit':
            result = self.lab.instruct(self.text, self.target, asynchronous=True)
            if result['accepted']:
                self.notice = (result['reason'] + '...') if result['mode'] == 'translating' else \
                    'Goal submitted. Interpretation and assumptions appear in the project panel.'
                self.focus, self.tab, self.scroll, self.project_selected = False, 'project', 0, None
                if not self.speed:
                    self.speed = 1
            else:
                self.notice = result['reason']

    def handle(self, event):
        pg = self.pg
        if event.type == pg.QUIT:
            return False
        if event.type == pg.VIDEORESIZE:
            self.screen = pg.display.set_mode((max(1120, event.w), max(760, event.h)), pg.RESIZABLE)
        if event.type == pg.MOUSEBUTTONDOWN:
            if event.button == 3:
                self.drag = event.pos
            if event.button == 1:
                self.focus = self.input_rect.collidepoint(event.pos)
                for rect, action in self.buttons:
                    if rect.collidepoint(event.pos):
                        self.perform(*action)
                        return True
                if self.canvas.collidepoint(event.pos):
                    for rect, identity in reversed(self.hits):
                        if rect.collidepoint(event.pos):
                            self.selected, self.scroll = identity, 0
                            if identity in self.view['observations']:
                                self.target, self.tab = identity, 'object'
                            else:
                                self.tab = 'project' if identity == self.lab.actor else 'object'
                            break
        if event.type == pg.MOUSEBUTTONUP and event.button == 3:
            self.drag = None
        if event.type == pg.MOUSEMOTION and self.drag:
            self.pan[0] += event.pos[0] - self.drag[0]
            self.pan[1] += event.pos[1] - self.drag[1]
            self.drag = event.pos
        if event.type == pg.MOUSEWHEEL:
            pos = pg.mouse.get_pos()
            if self.panel.collidepoint(pos):
                self.scroll = max(0, min(len(self.wrap(self.panel_lines(), 40)) - 1, self.scroll - event.y * 3))
            elif pos[1] >= self.screen.get_height() - 213:
                self.event_scroll = max(0, min(max(0, len(self.history) - 5), self.event_scroll + event.y * 3))
            else:
                self.zoom = max(35, min(240, self.zoom * 1.1 ** event.y))
        if event.type == pg.TEXTINPUT and self.focus:
            self.text = (self.text + event.text)[:4000]
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_F5:
                self.perform('save')
            elif event.key == pg.K_F9:
                self.perform('load')
            elif event.key == pg.K_F3:
                self.perform('debug')
            elif self.focus:
                if event.key == pg.K_RETURN:
                    self.perform('submit')
                elif event.key == pg.K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.key == pg.K_a and event.mod & pg.KMOD_CTRL:
                    self.text = ''
                elif event.key == pg.K_ESCAPE:
                    self.focus = False
            elif event.key == pg.K_SPACE:
                self.perform('speed', 0 if self.speed else self.last_speed)
            elif event.key in (pg.K_1, pg.K_2, pg.K_3):
                self.perform('speed', {pg.K_1: 1, pg.K_2: 5, pg.K_3: 20}[event.key])
            elif event.key == pg.K_n:
                self.lab.tick(asynchronous=True)
            elif event.key == pg.K_p:
                self.pause_experiment = not self.pause_experiment
            elif event.key == pg.K_ESCAPE:
                self.lab.stop('Stopped by player')
            elif event.key in (pg.K_LEFTBRACKET, pg.K_RIGHTBRACKET):
                projects = list(self.view['projects'])
                if projects:
                    current = self.project_selected or self.lab.project_id
                    index = projects.index(current) if current in projects else 0
                    self.project_selected = projects[(index + (1 if event.key == pg.K_RIGHTBRACKET else -1)) % len(projects)]
                    self.tab, self.scroll = 'history', 0
        return True

    def advance(self, dt):
        if not self.focus:
            keys = self.pg.key.get_pressed()
            self.pan[0] += (keys[self.pg.K_LEFT] - keys[self.pg.K_RIGHT]) * dt * 250
            self.pan[1] += (keys[self.pg.K_UP] - keys[self.pg.K_DOWN]) * dt * 250
        if not self.speed:
            return
        self.credit = min(30, self.credit + dt * self.speed)
        if self.credit >= 1:
            before = self.lab.view['time']
            changed = self.lab.tick(asynchronous=True)
            if changed:
                self.credit -= max(1, self.lab.view['time'] - before)
                self.update_cache()
                project = self.lab.project
                agenda = self.lab.agenda
                more = agenda and project and project['status'] == 'succeeded' and len(agenda['projects']) < len(agenda['steps'])
                if project and project['status'] in TERMINAL and not more:
                    self.notice = 'Engineer: ' + reply(project, self.lab.last_error)['headline']
                if self.pause_experiment and self.history and 'experiment' in self.history[-1]['metadata']:
                    self.speed = 0


def play(lab=None, save_path='runs/laboratory.json', smoke_frames=0, screenshot=None):
    try:
        client = Client(lab or Laboratory(), save_path)
    except ImportError as error:
        raise ValueError('Install the optional client: python -m pip install -e ".[play]"') from error
    pg = client.pg
    clock = pg.time.Clock()
    frames, running = 0, True
    try:
        client.draw()
        while running:
            dt = clock.tick(60) / 1000
            for event in pg.event.get():
                running = client.handle(event) and running
            client.advance(dt)
            client.draw()
            frames += 1
            if smoke_frames and frames >= smoke_frames:
                running = False
        if screenshot:
            Path(screenshot).parent.mkdir(parents=True, exist_ok=True)
            pg.image.save(client.screen, str(screenshot))
    finally:
        client.lab.close()
        pg.quit()
