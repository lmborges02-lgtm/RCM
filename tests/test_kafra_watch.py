import unittest
from pathlib import Path
from kafra_watch import merge_quotes, read_json, valuation


class KafraPriceTests(unittest.TestCase):
    def test_reference_and_unpriced_items(self):
        reference = read_json(Path(__file__).resolve().parents[1] / 'data' / 'npc-renewal.json')
        self.assertGreater(len(reference), 8000)
        rows = valuation([['Poção', 'Item', 3, 501], ['Sem ID', 'Item', 2]], reference, {})
        self.assertEqual(rows[0][3:], (reference['501'] * 124 // 100, 'rAthena'))
        self.assertEqual(rows[1][3:], (None, 'Sem cotação'))

    def test_latest_npc_price_overrides_reference_and_rounds_per_item(self):
        quotes = {}
        for price, when in ((50, 100), (99, 102), (50, 101), (30, 120)):
            merge_quotes(quotes, [{'updated_at': 104, 'quotes': {'501': [price, when]}}])
        _, _, qty, unit, source = valuation([['Poção', 'Item', 10, 501]], {'501': 50}, quotes)[0]
        self.assertEqual((qty * unit, source), (1220, 'NPC confirmado'))
