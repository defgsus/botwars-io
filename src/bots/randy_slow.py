"""
A truly random bot
"""

from src.bots.botbase import *


class Game(GameBase):

    def step(self):
        for bot in self.friends:

            action = None

            for e in self.enemies:
                if bot.distance(e) < 1.1:
                    action = bot.action("A", bot.direction(e))
                    break

            if not action:
                if self.frame % 5 == 0:
                    action = bot.action("M", self.rand.choice(list(DIRECTIONS)))
                else:
                    action = bot.action("D")

            self.add_action(action)


if __name__ == "__main__":
    process_stdin_stdout(Game)
