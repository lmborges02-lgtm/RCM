import json
from pathlib import Path
import tempfile
import unittest
from openkore_status import read_status


class StatusTests(unittest.TestCase):
    def test_missing_and_stale_never_allow_recovery(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.json'
            self.assertEqual(read_status(path, 100)['state'], 'unknown')
            path.write_text(json.dumps({'version': 1, 'state': 'offline', 'updated_at': 10, 'recoverable': True}))
            self.assertFalse(read_status(path, 100)['recoverable'])

    def test_fresh_offline_and_online_are_distinct(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.json'
            for state in ('online', 'offline'):
                path.write_text(json.dumps({'version': 1, 'state': state, 'updated_at': 100, 'recoverable': True}))
                self.assertEqual(read_status(path, 105)['state'], state)

    def test_big_or_partial_files_are_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.json'
            for raw in ('x' * 5000, '{', '{"updated_at":"NaN"}'):
                path.write_text(raw)
                self.assertEqual(read_status(path, 100)['state'], 'unknown')

    def test_initial_offline_is_not_recoverable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'status.json'
            path.write_text(json.dumps({'version': 1, 'state': 'offline', 'updated_at': 100, 'recoverable': False}))
            self.assertFalse(read_status(path, 100)['recoverable'])
