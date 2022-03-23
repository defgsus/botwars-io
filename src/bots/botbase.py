import sys
import math
import random
from typing import Optional, Union, List, Tuple, Set, Type


DIRECTIONS = {
    "N": (0, 1),
    "E": (1, 0),
    "S": (0, -1),
    "W": (-1, 0),
}

SPAWNS = [
    (4, 4), (4, 11), (11, 4), (11, 1)
]


def distance(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


class Action:
    def __init__(self, bot, *args: str):
        self.bot: Bot = bot
        self.args = tuple(str(a) for a in args)

    def __repr__(self):
        return "-".join(
            (f"{self.bot.x+1}:{self.bot.y+1}",) + self.args
        )


class Bot:
    def __init__(self, code: str, player_id: int):
        args = code.split("-")
        self.friend = args[0] == "F"
        self.x, self.y = (int(a) - 1 for a in args[1].split(":"))
        self.energy = int(args[2])
        self.player = player_id if self.friend else 1 - player_id
        self.index = 0
        # to test bots against themselves with slight modifications
        self.debug_switch = player_id == 0

    @property
    def pos(self) -> Tuple[int, int]:
        return self.x, self.y

    def action(self, *args: str) -> Action:
        return Action(self, *args)

    def __repr__(self):
        return f"{chr(ord('a') + self.player)}{self.x}:{self.y}"

    def distance(self, other: Union[Tuple[int, int], "Bot"]) -> float:
        if isinstance(other, Bot):
            x, y = other.x, other.y
        else:
            x, y = other
        return distance(self.x, self.y, x, y)

    def direction(self, other: Union[Tuple[int, int], "Bot"]) -> str:
        if isinstance(other, Bot):
            x, y = other.x, other.y
        else:
            x, y = other
        dx, dy = x - self.x, y - self.y
        if abs(dx) > abs(dy):
            return "E" if dx > 0 else "W"
        else:
            return "N" if dy > 0 else "S"


class GameBase:
    WIDTH = 16
    HEIGHT = 16

    def __init__(self, input: str):
        input_args = input.strip().split("#")

        self.frame, self.max_frame, self.player_id = list(int(a) for a in input_args[0].split(","))[:3]
        self.player_id -= 1

        self.bots: List[Bot] = [
            Bot(b, self.player_id)
            for b in input_args[1].split(",")
            if b
        ]
        self.friends: List[Bot] = [b for b in self.bots if b.friend]
        self.enemies: List[Bot] = [b for b in self.bots if not b.friend]
        for i, b in enumerate(self.friends):
            b.index = i
        for i, b in enumerate(self.enemies):
            b.index = i

        self.rand = random.SystemRandom()
        self.actions = []
        self.attacked_fields = []
        self.moved_fields = []

    def log(self, *args):
        print(*args, file=sys.stderr)

    def step(self):
        raise NotImplementedError

    def output(self):
        return ",".join(str(a) for a in self.actions)

    def add_action(self, a: Action):
        self.actions.append(a)
        if a.args[0] == "M":
            dx, dy = DIRECTIONS[a.args[1]]
            x, y = a.bot.x + dx, a.bot.y + dy
            self.moved_fields.append((x, y))
        elif a.args[0] == "A":
            dx, dy = DIRECTIONS[a.args[1]]
            x, y = a.bot.x + dx, a.bot.y + dy
            self.attacked_fields.append((x, y))

    def sorted_bots(
            self,
            bots: Optional[List[Bot]],
            distance_to: Optional[Union[Tuple[int, int], Bot]] = None,
            energy: bool = False,
    ) -> list:
        if bots is None:
            bots = self.bots.copy()
        if distance_to:
            if isinstance(distance_to, Bot):
                x, y = distance_to.x, distance_to.y
            else:
                x, y = distance_to
            bots = sorted(bots, key=lambda b: abs(b.x - x) + abs(b.y - y))
        if energy:
            bots = sorted(bots, key=lambda b: b.energy)
        return bots

    def get_map(self, x: int, y: int) -> Optional[Union[bool, Bot]]:
        if not 1 <= x < self.WIDTH-1 or not 1 <= y < self.HEIGHT-1:
            return True
        if x == 1 and (y == 1 or y == self.HEIGHT-2):
            return True
        if y == 1 and (x == 1 or x == self.WIDTH-2):
            return True
        for b in self.bots:
            if b.x == x and b.y == y:
                return b

    def astar_search(
            self,
            start_node: Tuple[int, int],
            end_node: Tuple[int, int],
            ignore: Optional[Set[Bot]] = None,
    ):
        """
        Get optimal path between start_node and end_node
        :param start_node: (int, int)
        :param end_node: (int, int)
        :param ignore: set of Bots to ignore
        :return: list of (int, int) or None
        """
        if ignore is None:
            ignore = tuple()

        def goal_cost_func(p1, p2):
            dx, dy = p1[0] - p2[0], p1[1] - p2[1]
            return abs(dx) + abs(dy)

        infinity = 2 << 31

        closed_set = set()
        open_set = {start_node}

        # cost of getting from start to this node
        g_score = {start_node: 0}

        # total cost if getting from start to end, through this node
        f_score = {end_node: goal_cost_func(start_node, end_node)}

        came_from = dict()

        while open_set:
            # pick smallest f from open_set
            current_node = None
            min_score = infinity
            for n in open_set:
                f = f_score.get(n, infinity)
                if f < min_score or current_node is None:
                    min_score, current_node = f, n
            open_set.remove(current_node)

            # found!
            if current_node == end_node:
                path = [current_node]
                while current_node in came_from:
                    current_node = came_from[current_node]
                    path.append(current_node)
                return list(reversed(path))

            # flag as evaluated
            closed_set.add(current_node)

            for neighbor_node, step_cost in self.adjacent_nodes(*current_node, ignore=ignore):

                if neighbor_node in closed_set:
                    continue

                if neighbor_node not in open_set:
                    open_set.add(neighbor_node)

                g = g_score.get(current_node) + step_cost
                # prune this path
                if g >= g_score.get(neighbor_node, infinity):
                    continue

                # continue this path
                came_from[neighbor_node] = current_node
                g_score[neighbor_node] = g
                f_score[neighbor_node] = g + goal_cost_func(neighbor_node, end_node)

        return None

    def adjacent_nodes(self, x: int, y: int, ignore: Set[Bot] = ()):
        for pos in (
                (x, y+1), (x+1, y), (x, y-1), (x-1, y)
        ):
            if pos not in self.attacked_fields and pos not in self.moved_fields:
                if pos not in SPAWNS:
                    m = self.get_map(*pos)
                    if not m or m in ignore:
                        friends = sum(1 for b in self.friends if b.distance(pos) <= 5)
                        cost = 1 - friends / len(self.friends)
                        yield pos, cost

    def test_explode(self, bot: Bot) -> Tuple[int, int]:
        energy_gain = -bot.energy
        bot_gain = -1
        for y in range(-1, 2):
            for x in range(-1, 2):
                if x or y:
                    other = self.get_map(bot.x + x, bot.y + y)
                    if isinstance(other, Bot):
                        sign = -1 if other.friend else 1
                        energy_gain += 6 * sign
                        if other.energy <= 8:
                            bot_gain += sign

        return bot_gain, energy_gain


def process_stdin_stdout(klass: Type[GameBase]):
    game = klass(sys.stdin.read().strip())
    game.step()
    print(game.output())
