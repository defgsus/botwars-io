import os
import traceback
import random
import subprocess
import importlib
from pathlib import Path
from typing import Union, Optional, List


class Bot:
    def __init__(self, player: int, x: int, y: int):
        self.player = player
        self.x = x
        self.y = y
        self.energy = 100
        self.defend = False
        self.attacked = False
        self.color = ""

    def __repr__(self):
        return f"{chr(ord('a') + self.player)}{self.x}:{self.y}"


class Simulator:
    """
    Simulates the matches at botwars.io

    Create a new instance for each match!
    """
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

    ATTACK = 12
    FRIENDLY_ATTACK = 8
    EXPLODE_ATTACK = 6

    COLOR1 = "\033[93m"
    COLOR2 = "\033[96m"
    COLOR_RED = "\033[91m"
    COLOR_OFF = "\033[m"

    def __init__(
            self,
            bot1: Union[str, Path],
            bot2: Union[str, Path],
            width: int = 16,
            height: int = 16,
            spawn_frame_interval: int = 10,
            random_probability: float = 0.,
    ):
        self.width = width
        self.height = height
        self.spawn_frame_interval = spawn_frame_interval
        self.random_probability = random_probability
        self.bot_files = [Path(bot1), Path(bot2)]
        self.bot_modules = []
        for f in self.bot_files:
            try:
                module = importlib.import_module(str(f).replace(os.sep, ".")[:-3])
                if hasattr(module, "Game"):
                    self.bot_modules.append(module)
                continue
            except ImportError:
                pass
            self.bot_modules.append(None)

        self.map = []
        self.bots = []
        self.spawn_points = [
            [(4, 4), (4, 11)],
            [(11, 4), (11, 11)],
        ]
        self.frame = 0
        self.stats = {
            key: [0] * len(self.bot_files)
            for key in (
                "defends", "useless_defends", "moves", "failed_moves",
                "enemy_attacks", "self_attacks", "missed_attacks",
                "enemy_kills", "self_kills",
                "explosions", "overspawned",
            )
        }
        self.user_data = [""] * len(self.bot_files)
        self.bot_genomes = [None] * len(self.bot_files)

        self.log_lines = []
        self.init_map()

    def init_map(self):
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
        self.log_lines = []
        self.log_lines.append(f"frame: {self.frame}")

        if self.frame % self.spawn_frame_interval == 0:
            self.spawn()
            self.log_lines.append("spawned")

        if self.frame == 0:
            self.frame += 1
            return

        # --- show map and process bots ---

        bot_outputs = []
        for i, (bot_file, bot_module) in enumerate(zip(self.bot_files, self.bot_modules)):
            input = self.game_state(i)
            if bot_module:
                output = self.process_module(bot_module, input, i).strip()
            else:
                output = self.process_file(bot_file, input).strip()

            output_args = output.split("#")
            bot_outputs.append(output_args[0])
            #print(f"INPUT player {i} : {input}")
            #print(f"OUTPUT player {i}: {output}")

            if len(output_args) > 1:
                self.user_data[i] = output_args[1]
            else:
                self.user_data[i] = ""

        # --- split action strings ---

        bot_actions = []
        for i, bot_output in enumerate(bot_outputs):
            if bot_output:
                for action in bot_output.split(","):
                    args = action.split("-")
                    x, y = (int(a) - 1 for a in args[0].split(":"))
                    bot = self.get_bot(x, y)
                    if bot and bot.player == i:
                        if self.random_probability and random.random() < self.random_probability:
                            bot_actions.append((bot, "move", [random.choice(list(self.DIRECTIONS))]))
                        else:
                            bot_actions.append((bot, self.ACTIONS[args[1]], args[2:]))

        # --- apply defend actions ---

        for bot in self.bots:
            bot.defend = False
            bot.attacked = False

        for bot, command, args in bot_actions:
            if command == "defend":
                bot.defend = True
                self.stats["defends"][bot.player] += 1

        # --- apply move actions ---

        move_targets = {}
        for bot, command, args in bot_actions:
            if command == "move":
                dx, dy = self.DIRECTIONS[args[0]]
                pos = bot.x + dx, bot.y + dy
                move_targets.setdefault(pos, []).append(bot)

        for pos, bots in move_targets.items():
            if not self.get_map(*pos) and len(bots) == 1:
                bots[0].x, bots[0].y = pos
                self.stats["moves"][bots[0].player] += 1
            else:
                for b in bots:
                    self.stats["failed_moves"][b.player] += 1

        # --- apply attack/explode actions ---

        for bot, command, args in bot_actions:
            if command == "attack":
                dx, dy = self.DIRECTIONS[args[0]]
                x, y = bot.x + dx, bot.y + dy
                other = self.get_bot(x, y)
                if other:
                    other.attacked = True
                    is_friendly = other.player == bot.player
                    energy = self.FRIENDLY_ATTACK if is_friendly else self.ATTACK
                    if other.defend:
                        energy //= 2
                    other.energy -= energy
                    self.log_lines.append(
                        f"{bot.color}{bot} attacked {other.color}{other}{self.COLOR_OFF}"
                    )
                    if is_friendly:
                        self.stats["self_attacks"][bot.player] += 1
                        if other.energy <= 0:
                            self.stats["self_kills"][bot.player] += 1
                    else:
                        self.stats["enemy_attacks"][bot.player] += 1
                        if other.energy <= 0:
                            self.stats["enemy_kills"][bot.player] += 1
                else:
                    self.stats["missed_attacks"][bot.player] += 1

            # TODO: bots always explode even if killed
            elif command == "explode":
                for y in range(-1, 2):
                    for x in range(-1, 2):
                        if x or y:
                            other = self.get_bot(bot.x + x, bot.y + y)
                            if other:
                                other.energy -= self.EXPLODE_ATTACK
                                if other.energy <= 0:
                                    if bot.player != other.player:
                                        self.stats["enemy_kills"][bot.player] += 1
                                    else:
                                        self.stats["self_kills"][bot.player] += 1
                bot.energy = 0
                self.stats["explosions"][bot.player] += 1
                self.log_lines.append(f"{self.COLOR_RED}{bot} exploded{self.COLOR_OFF}")

        for b in self.bots:
            if b.defend and not b.attacked:
                self.stats["useless_defends"][b.player] += 1

        died_bots = [
            b for b in self.bots
            if b.energy <= 0
        ]
        if died_bots:
            self.log_lines.append("died: " + ", ".join(str(b) for b in died_bots))

        self.bots = [
            b for b in self.bots
            if b.energy > 0
        ]
        self.log_lines.append("attacks (e/f): " + " ".join(
            f"{e}/{f}"
            for e, f in zip(self.stats["enemy_attacks"], self.stats["self_attacks"])
        ))
        self.log_lines.append("kills (e/f): " + " ".join(
            f"{e}/{f}"
            for e, f in zip(self.stats["enemy_kills"], self.stats["self_kills"])
        ))
        self.log_lines.append("bots: " + " ".join(str(n) for n in self.num_bots()))
        self.frame += 1

    def game_state(self, player: int) -> str:
        """
        State for each player.

        :param player: int, starts at 0
        """
        friends = [
            f"F-{b.x+1}:{b.y+1}-{b.energy}"
            for b in self.bots
            if b.player == player
        ]
        enemies = [
            f"E-{b.x+1}:{b.y+1}-{b.energy}"
            for b in self.bots
            if b.player != player
        ]
        elements = [
            f"{self.frame},100,{player+1}",
            ",".join(friends + enemies),
        ]
        if self.user_data[player]:
            elements.append(self.user_data[player][:128])

        return "#".join(elements)

    def get_map(self, x: int, y: int) -> Union[None, bool, Bot]:
        if not 0 <= x < self.width:
            return True
        if not 0 <= y <= self.height:
            return True
        if self.map[y][x]:
            return True
        return self.get_bot(x, y)

    def get_bot(self, x: int, y: int) -> Optional[Bot]:
        for b in self.bots:
            if b.x == x and b.y == y:
                return b

    def add_bot(self, player_index: int, x: int, y: int) -> Optional[Bot]:
        if self.get_map(x, y) is True:
            return None

        for i, b in enumerate(self.bots):
            if b.x == x and b.y == y:
                self.stats["overspawned"][b.player] += 1
                self.bots.pop(i)
                break

        bot = Bot(player_index, x, y)
        bot.color = self.COLOR1 if player_index == 0 else self.COLOR2
        self.bots.append(bot)
        return bot

    def num_bots(self) -> List[int]:
        num = [0] * len(self.bot_files)
        for b in self.bots:
            num[b.player] += 1
        return num

    def process_file(self, file: Path, input: str) -> str:
        #print("running", file)

        process = subprocess.Popen(
            ["python3", file.resolve()],
            #["jq"],
            cwd=file.parent,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            #env={**os.environ, "PYTHONPATH": str(file.parent)},
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

    def process_module(self, module, input: str, player: int) -> str:
        from .bots.botbase import GameBase
        try:
            game: GameBase = module.Game(input)

            if self.bot_genomes[player] is not None:
                game.set_genome(self.bot_genomes[player])

            game.step()

            if self.bot_genomes[player] is None:
                self.bot_genomes[player] = game.get_genome()

            return game.output()
        except:
            #import sys
            #traceback.print_exc()
            #traceback.print_exc(file=sys.stderr)
            raise

    def print(self, file=None):
        for y in range(self.height):
            y = self.height - 1 - y
            row = [f"{y:2} "]
            for x in range(self.width):
                m = self.get_map(x, y)
                if not m:
                    row.append(" . ")
                elif m is True:
                    row.append("###")
                elif isinstance(m, Bot):
                    color = self.COLOR1 if m.player == 0 else self.COLOR2
                    row.append(f"{color}{m.energy:3d}{self.COLOR_OFF}")

            row = "".join(row)
            y = len(self.log_lines) - 1 - y
            if 0 <= y < len(self.log_lines):
                row += " " + self.log_lines[y]

            print(row, file=file)

        print("   " + "".join(f"{x:2} " for x in range(self.width)), file=file)

