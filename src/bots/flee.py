"""
This bot tries to stay away
"""

from src.bots.botbase import *


class Game(GameBase):

    def step(self):
        for bot in self.friends:
            self.add_action(self.bot_flee(bot))

    def bot_flee(self, bot: Bot) -> Action:
        dist_map = self.enemy_distance_map

        best_dist, best_pos = None, None
        for y, row in enumerate(dist_map):
            for x, dist in enumerate(row):
                if not self.get_map(x, y) and (x, y) not in self.moved_fields:
                    if best_dist is None or dist > best_dist:
                        best_dist, best_pos = dist, (x, y)

        if best_pos:
            path = self.astar_search(
                bot.pos, best_pos,
                ignore=set(self.friends),
                enemy_distance_cost=True,
            )
            # self.log(bot, best_pos, path)
            if path and len(path) > 1:
                dir = bot.direction(path[1])
                return bot.action("M", dir)

        return bot.action("D")

    def adjacent_nodes(self, x: int, y: int, ignore: Set[Bot] = (), enemy_distance_cost: bool = False):
        for pos, cost in super().adjacent_nodes(x, y, ignore=ignore):

            if enemy_distance_cost:
                inv_dist = self.MAX_DISTANCE - self.enemy_distance_map[pos[1]][pos[0]]
                cost += inv_dist

            yield pos, cost


if __name__ == "__main__":
    process_stdin_stdout(Game)
