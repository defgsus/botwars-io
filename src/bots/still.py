"""
This bot does nothing except defending
"""

from src.bots.botbase import *


class Game(GameBase):

    def step(self):
        for bot in self.friends:
            self.add_action(bot.action("D"))


if __name__ == "__main__":
    process_stdin_stdout(Game)
