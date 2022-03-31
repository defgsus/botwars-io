"""
This bot does nothing except defending
"""

from src.bots.botbase import *


class GameState:

    WIDTH = 16
    HEIGHT = 16
    MAX_MANHATTEN_DISTANCE = WIDTH + HEIGHT

    rand = random.SystemRandom()

    class BotState:
        def __init__(self, x: int, y: int, energy: int, friend: bool):
            self.x = x
            self.y = y
            self.energy = energy
            self.friend = friend
            self.defend = False

        @property
        def pos(self) -> Tuple[int, int]:
            return self.x, self.y

        def copy(self) -> "BotState":
            return self.__class__(self.x, self.y, self.energy, self.friend)

    def __init__(self, bots: Iterable[BotState]):
        self.pos_to_bot = {
            (b.x, b.y): b
            for b in bots
        }
        self._performance_penalty = 0.

    def copy(self):
        return GameState(
            b.copy() for b in self.pos_to_bot.values()
        )

    def flip_player(self):
        for b in self.pos_to_bot.values():
            b.friend = not b.friend

    def apply_actions(self, actions: Sequence[Tuple[Tuple[int, int], Tuple[str, ...]]]):
        self._performance_penalty = 0.
        explosions = []
        move_targets = {}
        for pos, action in actions:
            bot = self.pos_to_bot[pos]
            if action[0] == "D":
                bot.defend = True
            elif action[0] == "S":
                explosions.append(pos)
            elif action[0] == "M":
                dx, dy = DIRECTIONS[action[1]]
                target_pos = bot.x + dx, bot.y + dy
                move_targets.setdefault(target_pos, []).append(bot)

        for pos, bots in move_targets.items():
            if len(bots) == 1 and not self.get_map(*pos):
                bots[0].x, bots[0].y = pos
            else:
                for b in bots:
                    if b.friend:
                        self._performance_penalty += 1

        self.pos_to_bot = {
            (b.x, b.y): b
            for b in self.pos_to_bot.values()
        }

        for pos, action in actions:
            if action[0] == "A":
                bot = self.pos_to_bot[pos]
                dx, dy = DIRECTIONS[action[1]]
                target_pos = bot.x + dx, bot.y + dy
                other_bot = self.pos_to_bot.get(target_pos)
                if not other_bot:
                    pass
                    #if bot.friend:
                    #    self._performance_penalty += 1
                else:
                    attack = 8 if bot.friend == other_bot.friend else 12
                    if other_bot.defend:
                        attack //= 2
                    other_bot.energy -= attack
                    if bot.friend and other_bot.friend:
                        self._performance_penalty += 5

        for pos in explosions:
            for y in range(-1, 2):
                for x in range(-1, 2):
                    if x or y:
                        bot = self.pos_to_bot.get((pos[0] + x, pos[1] + y))
                        if bot:
                            bot.energy -= 3 if bot.defend else 6

            self.pos_to_bot[pos].energy = 0

        for b in self.pos_to_bot.values():
            if b.friend and b.energy <= 0:
                self._performance_penalty += 3

        self.pos_to_bot = {
            (b.x, b.y): b
            for b in self.pos_to_bot.values()
            if b.energy > 0
        }

    def get_map(self, x: int, y: int) -> Union[bool, BotState]:
        pos = (x, y)
        if pos in self.pos_to_bot:
            return self.pos_to_bot[pos]

        if not 1 <= x < self.WIDTH-1 or not 1 <= y < self.HEIGHT-1:
            return True
        if (x == 1 or x == self.WIDTH-2) and (y == 1 or y == self.HEIGHT-2):
            return True

        return False

    def iter_actions(self, friend: bool) -> Generator[Tuple[BotState, List[Tuple[str, ...]]], None, None]:
        for bot in self.pos_to_bot.values():
            if bot.friend is friend:

                num_enemies_around = 0
                for other in self.pos_to_bot.values():
                    if other.friend != bot.friend:
                        if manhatten_distance(bot.x, bot.y, other.x, other.y) <= 2:
                            num_enemies_around += 1

                actions = []

                if num_enemies_around:
                    # actions.append("D")
                    actions.append("S")

                for dir, (dx, dy) in DIRECTIONS.items():
                    x, y = bot.x + dx, bot.y + dy
                    m = self.get_map(x, y)

                    # avoid moving against or attacking a wall
                    if m is not True:
                        actions.append(("M", dir))
                        if num_enemies_around:
                            actions.append(("A", dir))

                yield bot, actions

    def iter_next_states(self) -> Generator[
            Tuple[
                "GameState",
                Tuple[Tuple[Tuple[int, int], Tuple[str, ...]], ...],
            ]
            , None, None
    ]:
        friend_actions = {}
        for bot, actions in self.iter_actions(friend=True):
            friend_actions[bot] = actions

        own_actions_yielded = set()
        for i in range(50 * max(1, len(friend_actions))):
            new_state = self.copy()

            own_actions = []
            for bot, actions in friend_actions.items():
                action = self.rand.choice(actions)
                own_actions.append((bot.pos, action))

            own_actions = tuple(own_actions)
            if own_actions not in own_actions_yielded:
                own_actions_yielded.add(own_actions)

                new_state.apply_actions(own_actions)
                yield new_state, own_actions

    def evaluate(self) -> float:
        energy_score = 0.
        bot_alive_score = 0
        num_enemies = 0
        for b in self.pos_to_bot.values():
            if b.friend:
                energy_score += b.energy
                bot_alive_score += 1
            else:
                energy_score -= b.energy
                bot_alive_score -= 1
                num_enemies += 1
        energy_score /= 100.

        distance_score = 0.
        min_dist = None

        for b1 in self.pos_to_bot.values():
            if b1.friend:
                for b2 in self.pos_to_bot.values():
                    if not b2.friend:
                        dist = manhatten_distance(b1.x, b1.y, b2.x, b2.y) / self.MAX_MANHATTEN_DISTANCE
                        distance_score += 1. - dist
                        #if min_dist is None or dist < min_dist:
                        #    min_dist = dist

        #if min_dist is not None:
        #    distance_score += 1. - min_dist

        distance_score /= math.pow(max(1, len(self.pos_to_bot)), 2)

        return (
            energy_score
            + bot_alive_score
            + .2 * distance_score
            - .1 * self._performance_penalty
        )

    def get_best_next_state(self):
        best_score, best_state, best_actions = None, None, None
        for state1, actions in self.iter_next_states():
            score1 = state1.evaluate()

            if best_score is None or score1 >= best_score:
                best_score, best_state, best_actions = score1, state1, actions

        return best_score, best_state, best_actions

    def get_best_actions(self):
        init_score = self.evaluate()

        best_score, best_actions = None, None
        for state1, actions in self.iter_next_states():
            friend_score1 = state1.evaluate()

            if friend_score1 >= init_score:
                state1.flip_player()

                score2, state2, action2 = state1.get_best_next_state()
                if not state2:
                    if best_score is None or friend_score1 > best_score:
                        best_score, best_actions = friend_score1, actions

                else:
                    state2.flip_player()

                    for state3, _ in state2.iter_next_states():
                        friend_score3 = state3.evaluate()

                        if best_score is None or friend_score3 > best_score:
                            best_score, best_actions = friend_score3, actions

        return best_score, best_actions


class Game(GameBase):

    def step(self):

        state = GameState(
            GameState.BotState(b.x, b.y, b.energy, b.friend)
            for b in self.bots
        )

        score, actions = state.get_best_actions()
        self.log(score, actions)
        if actions:
            for pos, args in actions:
                self.add_action(
                    self.pos_to_friend_map[pos].action(*args)
                )


if __name__ == "__main__":
    process_stdin_stdout(Game)
