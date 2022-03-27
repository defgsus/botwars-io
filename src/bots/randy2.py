"""
Random bot walking along direction via user-data.

Each bot puts a string like `x:y-d` in the user-data,
meaning: bot at x:y has direction d.

The problem with addressing bots in the next frame is
that they *might* have moved but one can not be sure.
So if the bot has issued a move command the potential
next position is stored as well and both positions
are used to identify the bot in the next frame.
"""

from src.bots.botbase import *


class Game(GameBase):

    def get_user_data(self) -> str:
        entries = []
        for bot in self.friends:
            x, y = bot.pos
            for a in self.actions:
                if a.bot == bot and a.args[0] == "M":
                    dx, dy = DIRECTIONS[a.args[1]]
                    nx, ny = x + dx, y + dy
                    if nx != x:
                        x = f"{x}/{nx}"
                    if ny != y:
                        y = f"{y}/{ny}"

            entries.append(f"{x}:{y}-{bot.current_dir}")

        # limit the amount of user-data to the allowed 128 characters
        while entries and len(",".join(entries)) > 128:
            # self.log(f"user-data too long, dropping {entries[-1]}")
            entries.pop()

        return ",".join(entries)

    def set_user_data(self, data: str):
        for b in self.friends:
            b.current_dir = self.rand.choice(list(DIRECTIONS))

        if data:
            for entry in data.split(","):
                entry = entry.split("-")
                dir = entry[1]
                x1, y1 = entry[0].split(":")
                x2, y2 = x1, y1
                if "/" in x1:
                    x1, x2 = x1.split("/")
                if "/" in y1:
                    y1, y2 = y1.split("/")

                pos1 = int(x1), int(y1)
                pos2 = int(x2), int(y2)

                found = False
                for b in self.friends:
                    if b.pos == pos1 or b.pos == pos2:
                        b.current_dir = dir
                        found = True
                if not found:
                    pass
                    # bot probably died
                    # self.log("NOT FOUND", xy1, xy2)

    def step(self):
        # it's a good idea to shuffle the order of bots to process
        #   because one might step into the other's way and
        #   shuffling makes this fair for all
        self.rand.shuffle(self.friends)

        for bot in self.friends:

            action = None

            # -- fight close enemies --

            for e in self.enemies:
                if bot.distance(e) < 1.1:
                    bot.current_dir = bot.direction(e)
                    action = bot.action("A", bot.current_dir)
                    break

            # -- move along line --

            if not action:
                dx, dy = DIRECTIONS[bot.current_dir]
                x, y = bot.x + dx, bot.y + dy
                if (
                        not self.get_map(x, y)
                        and (x, y) not in self.attacked_fields
                        and (x, y) not in self.moved_fields
                ):
                    action = bot.action("M", bot.current_dir)
                else:
                    new_dirs = [d for d in DIRECTIONS if bot.current_dir != d]
                    self.rand.shuffle(new_dirs)
                    while new_dirs and not action:
                        d = new_dirs.pop()
                        dx, dy = DIRECTIONS[d]
                        x, y = bot.x + dx, bot.y + dy
                        if not self.get_map(x, y) and (x, y) not in self.attacked_fields:
                            action = bot.action("M", d)
                            bot.current_dir = d
                            break

                    if not action:
                        bot.current_dir = self.rand.choice(list(DIRECTIONS))
                        # self.log(f"{bot} blocked, new dir {bot.current_dir}")
                        action = bot.action("D")

            self.add_action(action)


if __name__ == "__main__":
    process_stdin_stdout(Game)
