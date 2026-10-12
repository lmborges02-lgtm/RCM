import importlib.util
import json
from pathlib import Path
import queue
import tempfile
from types import SimpleNamespace
import unittest


def module():
    source = Path(__file__).resolve().parents[1] / 'monitor.py'
    spec = importlib.util.spec_from_file_location('monitor_under_test', source)
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


class ConfigurationTests(unittest.TestCase):
    def test_first_run_creates_empty_config(self):
        m = module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            self.assertEqual(m.load_config(path), {'clients': [], 'restart_interval': 60})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')), m.load_config(path))

    def test_existing_config_is_not_overwritten(self):
        m = module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            content = '{"clients": [], "restart_interval": 120}'
            path.write_text(content, encoding='utf-8-sig')
            before = path.read_bytes()
            self.assertEqual(m.load_config(path)['restart_interval'], 120)
            self.assertEqual(path.read_bytes(), before)

    def test_invalid_config_is_preserved_and_rejected(self):
        m = module()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text('{"clients": null}', encoding='utf-8')
            with self.assertRaises(ValueError):
                m.load_config(path)
            self.assertEqual(path.read_text(encoding='utf-8'), '{"clients": null}')


class ActivityTests(unittest.TestCase):
    def test_static_first_capture_never_arms_detection(self):
        m = module(); activity = m.Activity()
        self.assertEqual(activity.observe(bytes([10] * 300), 10), 0)
        self.assertEqual(activity.observe(bytes([10] * 300), 1000), 990)
        self.assertFalse(activity.armed)

    def test_change_arms_and_resets_elapsed_time(self):
        m = module(); activity = m.Activity()
        activity.observe(bytes([10] * 300), 10)
        self.assertEqual(activity.observe(bytes([30] * 300), 20), 0)
        self.assertTrue(activity.armed)
        self.assertEqual(activity.observe(bytes([30] * 300), 140), 120)
        self.assertEqual(activity.observe(bytes([60] * 300), 141), 0)

    def test_crash_titles_are_specific(self):
        m = module()
        self.assertTrue(m.is_crash_title('Gravity(tm) Error Handler'))
        self.assertTrue(m.is_crash_title(' GRAVITY ERROR HANDLER '))
        self.assertFalse(m.is_crash_title('Ragnarok'))
        self.assertFalse(m.is_crash_title('Other Error Handler'))


class QueueTests(unittest.TestCase):
    def scenario(self, kind, interval=60):
        m = module(); clock = SimpleNamespace(now=0)
        launches, kills, samples = [], [], {}
        inventory = {} if kind == 'closed' else {
            i: {'ProcessId': 100 + i, 'CreationDate': str(i), 'client': str(i)} for i in range(5)}
        outer = self
        class Stop:
            stopped = False
            def is_set(self): return self.stopped
            def set(self): self.stopped = True
            def wait(self, seconds):
                clock.now += seconds
                outer.assertLess(clock.now, 2000, 'Fila não concluiu a simulação')
        stop = Stop()
        m.time = SimpleNamespace(monotonic=lambda: clock.now)
        m.processes = lambda: list(inventory.values())
        m.resolve = lambda path: {'Target': 'Ragexe.exe', 'Arguments': path.split('.')[0]}
        m.matches = lambda proc, target: proc['client'] == target['Arguments']
        m.argv = lambda text: text.split()
        m.crash_processes = lambda: {
            p['ProcessId'] for p in inventory.values() if kind == 'crash' and p['ProcessId'] < 500}
        def capture(pid, _):
            samples[pid] = samples.get(pid, 0) + 1
            return bytes([10 if samples[pid] == 1 else 30] * 300)
        m.read_capture = capture
        def terminate(proc):
            kills.append((clock.now, proc['client']))
            del inventory[int(proc['client'])]
        m.terminate_checked = terminate
        def launch(path):
            i = int(path.split('.')[0]); launches.append((clock.now, i))
            inventory[i] = {'ProcessId': 500 + i, 'CreationDate': 'new' + str(i), 'client': str(i)}
            if len(launches) == 5: stop.set()
        m.os = SimpleNamespace(path=SimpleNamespace(normcase=lambda value: value), startfile=launch)
        app = SimpleNamespace(
            items=[{'name': str(i), 'path': str(i) + '.lnk', 'enabled': True,
                    'visual': kind == 'frozen', 'roi': [0, 0, 100, 100], 'timeout': 30} for i in range(5)],
            settings={'restart_interval': interval}, events=queue.Queue(), stop=stop, is_admin=True)
        m.App.run(app)
        self.assertEqual(len(launches), 5)
        self.assertEqual(len({i for _, i in launches}), 5)
        for previous, current in zip(launches, launches[1:]):
            self.assertGreaterEqual(current[0] - previous[0], interval)
        if kind == 'crash':
            self.assertGreaterEqual(launches[0][0], 10)
            self.assertLess(launches[0][0], 90)
        self.assertEqual(len(kills), 0 if kind == 'closed' else 5)

    def test_five_closed_clients_restart_in_sequence(self):
        self.scenario('closed')

    def test_five_frozen_clients_restart_in_sequence(self):
        self.scenario('frozen')

    def test_crashes_restart_without_visual_detection(self):
        self.scenario('crash')

    def test_configured_interval_is_respected(self):
        self.scenario('closed', interval=120)

    def test_process_query_failure_never_launches_clients(self):
        m = module(); events = queue.Queue()
        class Stop:
            stopped = False
            def is_set(self): return self.stopped
            def wait(self, _): self.stopped = True
        def fail(): raise RuntimeError('Consulta indisponível')
        def unexpected(*_): self.fail('Uma ação foi executada sem leitura de processos')
        m.resolve = lambda _: {'Target': 'Ragexe.exe', 'Arguments': ''}
        m.processes = fail
        m.terminate_checked = unexpected
        m.os = SimpleNamespace(startfile=unexpected)
        app = SimpleNamespace(items=[{'name': 'Teste', 'path': 'ficticio.lnk', 'enabled': True}],
                              events=events, stop=Stop(), settings={'restart_interval': 60})
        m.App.run(app)
        self.assertTrue(any('Falha na leitura de processos' in str(event) for event in list(events.queue)))


if __name__ == '__main__':
    unittest.main()
