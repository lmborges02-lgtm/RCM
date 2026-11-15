import unittest
from urllib.parse import parse_qs
from kafra_sprite import sprite_query


class SpriteTests(unittest.TestCase):
    def test_layers_and_job_use_game_ids_only(self):
        query = parse_qs(sprite_query({
            'job': 4255, 'sex': 0, 'head': 3, 'top': 125, 'mid': 125,
            'low': 4, 'garment': 8, 'weapon': 2, 'shield': 1, 'bodyPalette': 2,
            'name': 'not sent',
        }))
        self.assertEqual(query['job'], ['4255'])
        self.assertEqual(query['gender'], ['female'])
        self.assertEqual(query['headgear'], ['4,125'])
        self.assertEqual(query['garment'], ['8'])
        self.assertEqual(query['weapon'], ['2'])
        self.assertEqual(query['shield'], ['1'])
        self.assertNotIn('name', query)

    def test_no_invented_class_or_hair_without_telemetry(self):
        self.assertIsNone(sprite_query({'job': 1, 'sex': 0}))
