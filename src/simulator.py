import subprocess
from pathlib import Path
from typing import Union, Optional, List


class Simulator:

    ACTIONS = {
        "A": "attack",
        "D": "defend",
        "M": "move",
        "S": "explode",
    }

    DIRECTIONS = {
        "N": (0, 1),
        "E": (1, 0),
        "S": (0, -1),
        "W": (-1, 0),
    }

    def __init__(
            self,
            bot1: Union[str, Path],
            bot2: Union[str, Path],
            width: int = 16,
            height: int = 16,
    ):
        self.width = width
        self.height = height
        self.bot_files = [Path(bot1), Path(bot2)]
        self.map = []
        self.bots = []
        self.spawn_points = [
            [(4, 4), (4, 11)],
            [(11, 4), (11, 11)],
        ]
        self._bot_id = 0
        self.frame = 0
        self.init_map()

    def init_map(self):
        self.frame = 0
        self.map = [
            [None] * self.width
            for _ in range(self.height)
        ]
        for i in range(self.width):
            self.map[0][i] = True
            self.map[-1][i] = True
        for i in range(self.height):
            self.map[i][0] = True
            self.map[i][-1] = True
        self.map[1][1] = True
        self.map[-2][1] = True
        self.map[-2][-2] = True
        self.map[1][-2] = True

    def spawn(self):
        for player_index, spawn_points in enumerate(self.spawn_points):
            for x, y in spawn_points:
                self.add_bot(player_index, x, y)

    def step(self):
        if self.frame % 10 == 0:
            self.spawn()

        if self.frame == 0:
            self.frame += 1
            return

        bot_outputs = []
        for i, bot_file in enumerate(self.bot_files):
            bot_outputs.append(self.process_file(bot_file, self.game_state(i)).strip())

        bot_actions = []
        for i, bot_output in enumerate(bot_outputs):
            for action in bot_output.split(","):
                args = action.split("-")
                x, y = (int(a) - 1 for a in args[0].split(":"))
                bot = self.get_bot(x, y)
                if bot and bot["player"] == i:
                    bot_actions.append((
                        bot,
                        self.ACTIONS[args[1]],
                        args[2:],
                    ))

        for bot, command, args in bot_actions:
            if command == "move":
                dx, dy = self.DIRECTIONS[args[0]]
                x, y = bot["x"] + dx, bot["y"] + dy
                if not self.get_map(x, y):
                    bot["x"], bot["y"] = x, y

            #elif command == ""
        self.frame += 1

    def game_state(self, player: int) -> str:
        """
        State for each player.

        :param player: int, starts at 0
        """
        friends = [
            f"F-{b['x']+1}:{b['y']+1}-{b['energy']}"
            for b in self.bots
            if b["player"] == player
        ]
        enemies = [
            f"E-{b['x']+1}:{b['y']+1}-{b['energy']}"
            for b in self.bots
            if b["player"] != player
        ]
        elements = [
            f"{self.frame},100,{player+1}",
            ",".join(friends + enemies),
        ]
        # TODO: user_data
        return "#".join(elements)

    def get_map(self, x: int, y: int) -> Union[None, bool, dict]:
        if not 0 <= x < self.width:
            return True
        if not 0 <= y <= self.height:
            return True
        if self.map[y][x]:
            return True
        return self.get_bot(x, y)

    def get_bot(self, x: int, y: int) -> Optional[dict]:
        for b in self.bots:
            if b["x"] == x and b["y"] == y:
                return b

    def add_bot(self, player_index: int, x: int, y: int) -> Optional[dict]:
        if self.get_map(x, y) is True:
            return None

        for i, b in enumerate(self.bots):
            if b["x"] == x and b["y"] == y:
                self.bots.pop(i)
                break

        self._bot_id += 1
        self.bots.append({
            "id": self._bot_id,
            "x": x,
            "y": y,
            "player": player_index,
            "energy": 100,
            "defend": False,
        })
        return self.bots[-1]

    def num_bots(self) -> List[int]:
        num = [0] * len(self.bot_files)
        for b in self.bots:
            num[b["player"]] += 1
        return num

    def process_file(self, file: Path, input: str) -> str:
        #print("running", file)

        process = subprocess.Popen(
            ["python3", file.resolve()],
            #["jq"],
            cwd=file.parent,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        try:
            process.stdin.writelines([input.encode()])
            process.stdin.close()

            output = process.stdout.read().decode()
            #print("got", output)
            return output
        except:
            process.kill()
            process.wait()
            raise

    def print(self, file=None):
        for y in range(self.height):
            row = []
            for x in range(self.width):
                m = self.get_map(x, y)
                if not m:
                    row.append(" . ")
                elif m is True:
                    row.append("###")
                elif isinstance(m, dict):
                    row.append(f"{m['energy']:3d}")

            row = "".join(row)
            if y == self.height - 2:
                row += f" frame: {self.frame}"
            if y == self.height - 1:
                row += " bots: " + " / ".join(str(n) for n in self.num_bots())
            print(row, file=file)
