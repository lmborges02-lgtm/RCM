import tempfile
import unittest
from pathlib import Path
from kafra_sessions import SessionHistory
from kafra_watch import valuation


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'sessions.sqlite3'
        self.store = SessionHistory(self.path)
        self.price = lambda items: valuation(items, {'501': 100}, {})

    def tearDown(self):
        self.folder.cleanup()

    def sample(self, stamp=3700, quantity=10, gains=90, token='one'):
        return dict(state='online', session=token, name='Demo', started_at=100,
                    updated_at=stamp, items=[['Item', 'Item', quantity, 501]], gains=gains)

    def observe(self, sample):
        return self.store.observe('source', 'profile', sample, self.price)

    def test_reset_archives_once_and_persists_baseline_on_reopen(self):
        self.observe(self.sample())
        self.assertTrue(self.store.reset('source', 'profile', self.sample(), self.price))
        self.assertFalse(self.store.reset('source', 'profile', self.sample(), self.price))
        self.store = SessionHistory(self.path)
        row = self.observe(self.sample(stamp=3710, quantity=13, gains=97))
        self.assertEqual((row['items'][0][2], row['gains'], row['started_at']), (3, 7, 3700))
        history = self.store.rows('source', 'profile', 'Demo')
        self.assertEqual(len(history), 2)
        self.assertEqual(history[1]['loot'], 1240)
        self.assertEqual(history[1]['closed'], 'Reset manual')

    def test_time_weighted_rate_not_mean_of_rates(self):
        self.observe(self.sample(stamp=3700, quantity=10))
        self.store.reset('source', 'profile', self.sample(), self.price)
        # A different natural session contains its own cumulative totals.
        other = dict(self.sample(stamp=5000, quantity=1, token='two'), started_at=3200)
        self.observe(other)
        summary = self.store.summary('source', 'profile', 'Demo')
        self.assertEqual(summary['loot'], 1364)
        self.assertEqual(summary['seconds'], 5400)
        self.assertEqual(summary['rate'], round(1364 * 3600 / 5400))

    def test_missing_signal_excludes_unobserved_gap_and_other_characters(self):
        self.observe(self.sample())
        self.store.close_missing('source', set())
        row = self.observe(self.sample(stamp=3800, quantity=20))
        self.assertEqual(row['items'], [])
        row = self.observe(self.sample(stamp=3810, quantity=22))
        self.assertEqual(row['items'][0][2], 2)
        other = dict(self.sample(stamp=3820), name='Other')
        self.observe(other)
        self.assertEqual(len(self.store.rows('source', 'profile', 'Other')), 1)
        self.assertEqual(len(self.store.rows('source', 'profile', 'Demo')), 2)

    def test_quotes_zero_counts_invalid_data_and_replayed_samples(self):
        self.assertIsNone(self.observe(dict(self.sample(), session=None)))
        self.observe(self.sample())
        self.observe(self.sample(stamp=3690, quantity=9))
        self.assertEqual(self.store.rows('source', 'profile', 'Demo')[0]['loot'], 1240)
