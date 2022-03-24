"""
Random bot walking along direction via user-data
"""

from src.bots.botbase import *


class Game(GameBase):

    def set_user_data(self, data: str):
        for b in self.friends:
            b.current_dir = self.rand.choice(list(DIRECTIONS))

        if data:
            for entry in data.split(","):
                entry = entry.split("-")
                xy1 = tuple(int(v) for v in entry[0].split(":"))
                dir = entry[-1]
                if len(entry) > 2:
                    xy2 = tuple(int(v) for v in entry[1].split(":"))
                else:
                    xy2 = xy1

                found = False
                for b in self.friends:
                    if b.pos == xy1 or b.pos == xy2:
                        b.current_dir = dir
                        found = True
                if not found:
                    pass
                    # bot probably died
                    # self.log("NOT FOUND", xy1, xy2)

    def get_user_data(self) -> str:
        entries = []
        for bot in self.friends:
            x, y = bot.pos
            entry = [f"{x}:{y}"]
            for a in self.actions:
                if a.bot == bot and a.args[0] == "M":
                    dx, dy = DIRECTIONS[a.args[1]]
                    entry.append(f"{x+dx}:{y+dy}")
                    break
            entry.append(bot.current_dir)
            entries.append("-".join(entry))
        return ",".join(entries)

    def step(self):
        for bot in self.friends:

            action = None

            for e in self.enemies:
                if bot.distance(e) < 1.1:
                    bot.current_dir = bot.direction(e)
                    action = bot.action("A", bot.current_dir)
                    break

            if not action:
                dx, dy = DIRECTIONS[bot.current_dir]
                x, y = bot.x + dx, bot.y + dy
                if not self.get_map(x, y):
                    action = bot.action("M", bot.current_dir)
                else:
                    bot.current_dir = self.rand.choice(list(DIRECTIONS))
                    action = bot.action("D")

            self.add_action(action)


if __name__ == "__main__":
    process_stdin_stdout(Game)
