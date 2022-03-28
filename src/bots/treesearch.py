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
        self._performance_score = 0.

    def copy(self):
        return GameState(
            b.copy() for b in self.pos_to_bot.values()
        )

    def flip_player(self):
        for b in self.pos_to_bot.values():
            b.friend = not b.friend

    def apply_actions(self, actions: List[Tuple[Tuple[int, int], Tuple[str, ...]]]):
        self._performance_score = 0.
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
                    self._performance_score += -1 if b.friend else 1

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
                    self._performance_score += -1 if bot.friend else 1
                else:
                    attack = 8 if bot.friend == other_bot.friend else 12
                    if other_bot.defend:
                        attack //= 2
                    other_bot.energy -= attack

        for pos in explosions:
            for y in range(-1, 2):
                for x in range(-1, 2):
                    if x or y:
                        bot = self.pos_to_bot.get((pos[0] + x, pos[1] + y))
                        if bot:
                            bot.energy -= 3 if bot.defend else 6

            self.pos_to_bot[pos].energy = 0

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
                actions = [
                    #("D",), ("S",)
                ]
                for dir, (dx, dy) in DIRECTIONS.items():
                    x, y = bot.x + dx, bot.y + dy
                    m = self.get_map(x, y)

                    # avoid moving against or attacking a wall
                    if m is not True:
                        actions.append(("A", dir))
                        actions.append(("M", dir))

                yield bot, actions

    def iter_next_states(self) -> Generator[
            Tuple[
                "GameState",
                Tuple[Tuple[Tuple[int, int], Tuple[str, ...]], ...],
            ]
            , None, None
    ]:
        friend_actions = {}
        enemy_actions = {}
        for bot, actions in self.iter_actions(friend=True):
            friend_actions[bot] = actions
        for bot, actions in self.iter_actions(friend=False):
            enemy_actions[bot] = actions

        all_actions_processed = set()
        for i in range(128 // max(1, len(friend_actions))):
            new_state = self.copy()

            all_actions = []
            own_actions = []
            for available_actions in (friend_actions, enemy_actions):
                for bot, actions in available_actions.items():
                    action = self.rand.choice(actions)
                    all_actions.append((bot.pos, action))
                    if bot.friend:
                        own_actions.append((bot.pos, action))

            all_actions = tuple(all_actions)
            own_actions = tuple(own_actions)
            if all_actions not in all_actions_processed:
                all_actions_processed.add(all_actions)

                new_state.apply_actions(all_actions)
                yield new_state, own_actions

    def evaluate(self) -> float:
        energy_score = 0.
        for b in self.pos_to_bot.values():
            if b.friend:
                energy_score += b.energy
            else:
                energy_score -= b.energy
        energy_score /= 100.

        distance_score = 0.
        for b1 in self.pos_to_bot.values():
            for b2 in self.pos_to_bot.values():
                if b1.friend and b1 != b2:
                    same_side = b1.friend == b2.friend
                    dist = manhatten_distance(b1.x, b1.y, b2.x, b2.y)# / self.MAX_MANHATTEN_DISTANCE
                    if dist <= 5:
                        dist /= 5
                        if same_side:
                            dist_score = .1 * (1. - dist)
                        else:
                            if b2.energy / 2 > b1.energy:
                                dist_score = dist
                            else:
                                dist_score = 1. - dist

                        #if not b1.friend:
                        #    dist_score = -dist_score

                        distance_score += dist_score

        distance_score /= max(1, len(self.pos_to_bot))

        return (
            energy_score
            + distance_score
            + .1 * self._performance_score
        )

    def get_best_actions(self):
        init_score = self.evaluate()

        best_score, best_actions = None, None
        for state1, actions in self.iter_next_states():
            score1 = state1.evaluate()

            if best_score is None or score1 >= best_score:
                best_score, best_actions = score1, actions

            """
            if score1 >= init_score:

                for state2, _ in state1.iter_next_states():

                    score2 = state2.evaluate()
                    if best_score is None or score2 > best_score:
                        best_score, best_actions = score2, actions
            """
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
