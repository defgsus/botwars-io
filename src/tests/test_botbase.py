import unittest

from src.bots.botbase import *


class TestBotBase(unittest.TestCase):

    def test_ulam_spiral(self):
        expected_spiral = [
            [16, 15, 14, 13, 12],
            [17,  4,  3,  2, 11],
            [18,  5,  0,  1, 10],
            [19,  6,  7,  8,  9],
            [20, 21, 22, 23, 24],
        ]
        spiral = [
            [0] * 5
            for _ in range(5)
        ]
        for i in range(5*5):
            x, y = GameBase.ulam_spiral(i)
            spiral[2-y][2+x] = i

        self.assertEqual(expected_spiral, spiral)