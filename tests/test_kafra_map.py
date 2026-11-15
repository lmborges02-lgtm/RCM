import unittest
from kafra_map import marker


class MapProjectionTests(unittest.TestCase):
    def test_centers_and_y_axis_in_a_rectangular_minimap(self):
        self.assertEqual(marker(0, 0, 100, 50, 10, 20, 200, 100), (11, 119))
        self.assertEqual(marker(99, 49, 100, 50, 10, 20, 200, 100), (209, 21))
