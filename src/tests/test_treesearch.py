import unittest

from src.bots.treesearch import *


class TestBotBase(unittest.TestCase):

    def test_ab_prune(self):
        state = GameState([
            GameState.BotState(5, 4, 100, friend=True),
            GameState.BotState(4, 5, 100, friend=True),
            GameState.BotState(5, 5, 100, friend=False),
        ])
        # self.assertEqual(0, state.evaluate())

        states = [
            (s.evaluate(), actions)
            for s, actions in state.iter_next_states()
        ]
        states.sort(key=lambda s: s[0])
        for score, actions in states:
            print(score, actions)

        print("best:", state.get_best_actions())