import sys
import math
import random
from typing import Optional, Union, List, Tuple, Set, Type, Any, Generator, Iterable


DIRECTIONS = {
    "N": (0, 1),
    "E": (1, 0),
    "S": (0, -1),
    "W": (-1, 0),
}

ACTIONS = {
    "m": "move",
    "d": "defend",
    "a": "attack",
    "s": "explode",
}

SPAWNS = [
    (4, 4), (4, 11), (11, 4), (11, 11)
]


def distance(x1: int, y1: int, x2: int, y2: int) -> float:
    return math.sqrt(math.pow(x1 - x2, 2) + math.pow(y1 - y2, 2))


def manhatten_distance(x1: int, y1: int, x2: int, y2: int) -> int:
    return abs(x1 - x2) + abs(y1 - y2)


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
    """
    Wrapper for one round of a bot match.

    will be inititalized with the game state and
    provides usefull data and methods for managing
    the round.

    The friendly bots must add their actions via .add_action() in the step() method.

    """
    WIDTH = 16
    HEIGHT = 16
    MAX_DISTANCE = math.sqrt(WIDTH * WIDTH + HEIGHT * HEIGHT)

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
        self.pos_to_bot_map = {
            bot.pos: bot
            for bot in self.bots
        }
        self.pos_to_friend_map = {
            bot.pos: bot
            for bot in self.friends
        }
        self.pos_to_enemy_map = {
            bot.pos: bot
            for bot in self.enemies
        }
        self.rand = random.SystemRandom()
        self.actions: List[Action] = []
        self.attacked_fields = []
        self.moved_fields = []
        self._deltas_by_distance = None
        self._enemy_distance_map = None
        self._friend_distance_map = None

        if len(input_args) > 2:
            self.set_user_data(input_args[2])
        else:
            self.set_user_data("")

    def log(self, *args, **kwargs):
        kwargs["file"] = sys.stderr
        print(*args, **kwargs)

    def progress(self) -> float:
        """
        Game (round) progress in range [0, 1]
        """
        return self.frame / self.max_frame

    # ------------ interface for derived classes -------------

    def step(self):
        raise NotImplementedError

    def get_user_data(self) -> str:
        """
        Override to export user-data after the round
        """
        return ""

    def set_user_data(self, data: str):
        """
        Override to handle user-data before the round.

        This method will be called with "" when no user-data is present.
        """
        pass

    # ---- evolution interface ----

    def get_genome(self) -> Any:
        pass

    def set_genome(self, genome: Any):
        pass

    def mutate(self, amount: float, probability: float):
        """
        Interface for evolution. Both values in range [0, 1]
        """
        pass

    # -------------------------------------------------------

    def output(self):
        output = ",".join(str(a) for a in self.actions)
        user_data = self.get_user_data()
        if user_data:
            output = f"{output}#{user_data}"
        return output

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
            reverse: bool = False
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

        if reverse:
            bots = list(reversed(bots))
        return bots

    def get_map(self, x: int, y: int) -> Optional[Union[bool, Bot]]:
        b = self.pos_to_bot_map.get((x, y))
        if b:
            return b
        if not 1 <= x < self.WIDTH-1 or not 1 <= y < self.HEIGHT-1:
            return True
        if (x == 1 or x == self.WIDTH-2) and (y == 1 or y == self.HEIGHT-2):
            return True

    @classmethod
    def ulam_spiral(cls, n: int) -> Tuple[int, int]:
        mm = int(0.5 * (math.sqrt(n) + 1.0))
        kk = n - 4 * mm * (mm - 1)
        if kk < 1 or kk > 8 * mm:
            return 0, 0
        if kk <= 2 * mm:
            return mm, kk - mm
        if kk <= 4 * mm:
           return 3 * mm - kk, mm
        if kk <= 6 * mm:
            return -mm, 5 * mm - kk
        return kk - 7 * mm, -mm

    @property
    def deltas_by_distance(self) -> List[Tuple[int, int]]:
        if not self._deltas_by_distance:
            self._deltas_by_distance = []
            distances = dict()
            for y in range(-self.HEIGHT // 2 - 1, self.HEIGHT // 2 + 1):
                for x in range(-self.WIDTH // 2 - 1, self.WIDTH // 2 + 1):
                    self._deltas_by_distance.append((x, y))
                    distances[(x, y)] = math.sqrt(x*x + y*y)

            self._deltas_by_distance.sort(key=lambda p: distances[p])

        return self._deltas_by_distance

    def get_next_free_pos(self, x: int, y: int, close_to: Optional[Tuple[int, int]] = None) -> Optional[Tuple[int, int]]:
        #for i in range(self.WIDTH * self.HEIGHT):
        #    ux, uy = self.ulam_spiral(i)
        for ux, uy in self.deltas_by_distance:
            ux += x
            uy += y
            if not self.get_map(ux, uy):
                return ux, uy

    @property
    def enemy_distance_map(self) -> List[List[float]]:
        if not self._enemy_distance_map:
            self._enemy_distance_map = []
            for y in range(self.WIDTH):
                row = []
                for x in range(self.HEIGHT):
                    if not self.enemies:
                        row.append(0.)
                    else:
                        row.append(
                            min([distance(x, y, e.x, e.y) for e in self.enemies])
                        )
                self._enemy_distance_map.append(row)
        return self._enemy_distance_map

    @property
    def friend_distance_map(self) -> List[List[float]]:
        if not self._friend_distance_map:
            self._friend_distance_map = []
            for y in range(self.WIDTH):
                row = []
                for x in range(self.HEIGHT):
                    if not self.friends:
                        row.append(0.)
                    else:
                        row.append(
                            min([distance(x, y, e.x, e.y) for e in self.friends])
                        )
                self._friend_distance_map.append(row)
        return self._friend_distance_map

    def get_move_positions(self, bot: Union[Tuple[int, int], Bot]) -> List[Tuple[int, int]]:
        """
        Return the absolute move-to positions of a bot or position,
        """
        return self.get_attack_positions(bot)

    def get_attack_positions(self, bot: Union[Tuple[int, int], Bot]) -> List[Tuple[int, int]]:
        """
        Return the absolute attack positions of a bot or position,
        """
        if isinstance(bot, Bot):
            x, y = bot.x, bot.y
        else:
            x, y = bot
        positions = []
        for dx, dy in DIRECTIONS.values():
            positions.append((x + dx, y + dy))
        return positions

    def get_diagonal_positions(self, bot: Union[Tuple[int, int], Bot]) -> List[Tuple[int, int]]:
        """
        Return the absolute positions of adjacent corners of a bot or position,
        """
        if isinstance(bot, Bot):
            x, y = bot.x, bot.y
        else:
            x, y = bot
        positions = []
        for dx, dy in ((-1, 1), (1, 1), (1, -1), (-1, -1)):
            positions.append((x + dx, y + dy))
        return positions

    def astar_search(
            self,
            start_node: Tuple[int, int],
            end_node: Tuple[int, int],
            ignore: Optional[Set[Bot]] = None,
            **kwargs,
    ):
        """
        Get optimal path between start_node and end_node

        :param start_node: (int, int)
        :param end_node: (int, int)
        :param ignore: set of Bots to ignore

        Any additional keyword arguments are passed to `adjacent_nodes` method

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

            for neighbor_node, step_cost in self.adjacent_nodes(*current_node, ignore=ignore, **kwargs):

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

    def adjacent_nodes(self, x: int, y: int, ignore: Set[Bot] = (), **kwargs):
        for pos in (
                (x, y+1), (x+1, y), (x, y-1), (x-1, y)
        ):
            m = self.get_map(*pos)
            if not m or m in ignore:
                yield pos, 1

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
                        if other.energy <= 6:
                            bot_gain += sign

        return bot_gain, energy_gain


def process_stdin_stdout(klass: Type[GameBase]):
    game = klass(sys.stdin.read().strip())
    game.step()
    print(game.output())
