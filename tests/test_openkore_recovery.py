import queue
from types import SimpleNamespace
import unittest
from test_monitor import module


class RecoveryTests(unittest.TestCase):
    def simulate(self, reconnect):
        m = module(); clock = SimpleNamespace(now=0); actions = []; reads = {}
        class Stop:
            stopped = False
            def is_set(self): return self.stopped
            def set(self): self.stopped = True
            def wait(self, seconds):
                clock.now += seconds
                if clock.now > 200: self.stopped = True
        stop = Stop()
        m.time = SimpleNamespace(monotonic=lambda: clock.now)
        proc = {'ProcessId': 123, 'CreationDate': 'fixture'}
        m.processes = lambda: [proc]
        m.crash_processes = lambda: set()
        m.resolve = lambda _: {'Target': 'game.exe', 'Arguments': ''}
        m.matches = lambda *_: True
        def report(_):
            reads[clock.now] = reads.get(clock.now, 0) + 1
            if reconnect and clock.now == 120 and reads[clock.now] > 1:
                stop.set()
                return {'state': 'online', 'recoverable': False, 'detail': ''}
            return {'state': 'offline', 'recoverable': True, 'detail': ''}
        m.read_status = report
        m.terminate_checked = lambda _: actions.append('terminate')
        def launch(_): actions.append('launch'); stop.set()
        m.os = SimpleNamespace(path=SimpleNamespace(normcase=lambda x: x), startfile=launch)
        app = SimpleNamespace(items=[{'name': 'Demo', 'path': 'demo.lnk', 'enabled': True,
                                     'openkore_status': 'demo.json', 'visual': True, 'timeout': 30}],
                              stop=stop, events=queue.Queue(), settings={'restart_interval': 60})
        m.App.run(app)
        return actions

    def test_offline_recovery_ignores_animated_sprites(self):
        self.assertEqual(self.simulate(False), ['terminate', 'launch'])

    def test_reconnection_cancels_pending_recovery(self):
        self.assertEqual(self.simulate(True), [])
