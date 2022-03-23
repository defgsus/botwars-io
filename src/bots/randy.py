"""
A truly random bot
"""

from src.bots.botbase import *


class Game(GameBase):

    def step(self):
        for bot in self.friends:
            action = bot.action("M", self.rand.choice(list(DIRECTIONS)))
            self.add_action(action)


if __name__ == "__main__":
    process_stdin_stdout(Game)
