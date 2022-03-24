import random
import pickle
from pathlib import Path
from copy import deepcopy
from multiprocessing import Pool
#from multiprocessing.pool import ThreadPool as Pool
from typing import Type, List, Tuple, Dict, Optional, Union, Any

from tqdm import tqdm
import tabulate

from .bots.botbase import GameBase
from .simulator import Simulator


class BotPool:

    def __init__(self):
        self.bot_files = {}
        self.population = {}
        self.generation = 0
        self._id_counter = 0
        self._id_counter_pop = 0
        self.rand = random.Random()
        self.num_processes = 8

    def save(self, filename: Union[str, Path]):
        with open(filename, "wb") as fp:
            pickle.dump({
                "bot_files": self.bot_files,
                "population": self.population,
                "generation": self.generation,
                "_id_counter": self._id_counter,
                "_id_counter_pop": self._id_counter_pop,
            }, fp)

    @classmethod
    def load(cls, filename: Union[str, Path]) -> "BotPool":
        with open(filename, "rb") as fp:
            data = pickle.load(fp)
        pool = BotPool()
        pool.bot_files = data["bot_files"]
        pool.population = data["population"]
        pool.generation = data["generation"]
        pool._id_counter = data["_id_counter"]
        pool._id_counter_pop = data["_id_counter_pop"]
        return pool

    def add_bot_file(self, *bot_file: Union[str, Path]):
        for fn in bot_file:
            fn = str(fn)

            id = chr(ord("A") + self._id_counter_pop % 26)
            self._id_counter_pop += 1

            sim = Simulator(fn, fn)
            if not sim.bot_modules[0]:
                raise NotImplementedError(f"Can only work with GameBase modules")
            sim.step()
            sim.step()

            self.bot_files[id] = {
                "id": id,
                "file": fn,
                "evolution": sim.bot_genomes[0] is not None,
                "genome": deepcopy(sim.bot_genomes[0]),
                "class": sim.bot_modules[0].Game,
                "stats": {},
            }

    def create_population(self, count: int = 10):
        assert list(filter(lambda p: p["evolution"], self.bot_files.values())), \
            "Need at least one mutatable type"

        source_count = dict()
        for i in range(count):
            self._id_counter_pop += 1
            id = self._id_counter_pop

            while True:
                source = self.rand.choice(list(self.bot_files.values()))
                if not source["evolution"] and source_count.get(source["file"]):
                    continue
                source_count[source["file"]] = source_count.get(source["file"], 0) + 1
                break

            genome = deepcopy(source["genome"])

            if source_count[source["file"]] > 1:
                source["genome"] = self.mutate(source["class"], source["genome"])

            self.population[id] = {
                "source_id": source["id"],
                "id": id,
                "parent": source["id"],
                "generation": 1,
                "file": source["file"],
                "class": source["class"],
                "evolution": source["evolution"],
                "genome": genome,
                "fitness": 0,
                "stats": {},
            }

    def select_population(self, num_best: int = 5, count: int = 10):
        assert count > num_best

        best_pops = sorted(
            [p for p in self.population.values() if p["evolution"]],
            key=lambda p: p["fitness"],
            reverse=True,
        )[:num_best]

        prev_population = self.population
        self.population = {
            pop["id"]: {
                **pop,
                "stats": {}
            }
            for pop in best_pops
        }

        # also add non-mutatables for comparison
        file_set = set()
        for p in prev_population.values():
            if not p["evolution"]:
                if p["file"] not in file_set:
                    file_set.add(p["file"])
                    self.population[p["id"]] = {
                        **p,
                        "stats": {},
                    }

        for i in range(count - len(self.population)):
            self._id_counter_pop += 1
            id = self._id_counter_pop

            pop = deepcopy(best_pops[i % len(best_pops)])
            pop["genome"] = self.mutate(pop["class"], pop["genome"])

            self.population[id] = {
                **pop,
                "id": id,
                "parent": pop["id"],
                "generation": pop["generation"] + 1,
                "fitness": 0,
                "stats": {},
            }

    def mutate(self, klass: Type[GameBase], genome: Any) -> Any:
        original_genome = genome
        bot: GameBase = klass("1,100,1#")
        bot.set_genome(deepcopy(genome))
        for i in range(100):
            bot.mutate(.2, .4)
            genome = bot.get_genome()
            if genome != original_genome:
                break
        return genome

    def evaluate(self):
        pairs = []
        for pop1 in self.population.values():
            for pop2 in self.population.values():
                if pop1 != pop2:
                    pairs.append((pop1, pop2))
                    #pairs.append((pop2, pop1))
        print("evaluating", len(pairs), "matches")
        if self.num_processes < 2:
            results = self._evaluate_pop_pairs(pairs)
        else:
            split_pairs = [
                [[], i]
                for i in range(self.num_processes)
            ]
            for i, pair in enumerate(pairs):
                split_pairs[i % self.num_processes][0].append(pair)

            results_list = Pool(self.num_processes).starmap(self._evaluate_pop_pairs, split_pairs)
            results = {}
            for r in results_list:
                for id, stats in r.items():
                    if id not in results:
                        results[id] = stats
                    else:
                        for key, value in stats.items():
                            results[id][key] = results[id].get(key, 0) + value

        for id, stats in results.items():
            pop = self.population[id]
            for key, value in stats.items():
                pop["stats"][key] = pop["stats"].get("key", 0) + value

        for pop in self.population.values():
            wins = pop["stats"].get("wins", 0)
            defeats = pop["stats"].get("defeats", 0)
            kills = pop["stats"].get("enemy_kills", 0)
            pop["fitness"] = wins - defeats + kills / 5.

        self.generation += 1

    def _evaluate_pop_pairs(self, pairs: List[Tuple[dict, dict]], tqdm_position=None) -> dict:
        results = {}
        for pop1, pop2 in tqdm(pairs, desc=f"evaluating #{self.generation}", position=tqdm_position):
            sim = Simulator(pop1["file"], pop2["file"])
            sim.bot_genomes[0] = pop1["genome"]
            sim.bot_genomes[1] = pop2["genome"]

            for i in range(100):
                sim.step()

            n1, n2 = sim.num_bots()

            for i, id in enumerate((pop1["id"], pop2["id"])):
                if id not in results:
                    results[id] = {
                        "wins": 0,
                        "defeats": 0,
                        "draws": 0,
                        "matches": 0,
                    }

                results[id]["matches"] += 1

                for key, values in sim.stats.items():
                    results[id][key] = results[id].get(key, 0) + values[i]

            if n1 > n2:
                results[pop1["id"]]["wins"] += 1
                results[pop2["id"]]["defeats"] += 1
            elif n1 < n2:
                results[pop1["id"]]["defeats"] += 1
                results[pop2["id"]]["wins"] += 1
            else:
                results[pop1["id"]]["draws"] += 1
                results[pop2["id"]]["draws"] += 1

        return results

    def _create_genome(self, klass: Type[GameBase]) -> Any:
        bot = klass("1,100,1#")
        bot.get_genome()

    def dump_files(self):
        rows = []
        for b in self.bot_files.values():
            rows.append({
                "id": b["id"],
                "file": b["file"],
                "evo?": b["evolution"],
                "genome": str(b["genome"])[:30],
            })
        print(tabulate.tabulate(rows, headers="keys", tablefmt="presto") + "\n")

    def dump_population(self):
        rows = []
        for b in self.population.values():
            rows.append({
                "source": b["source_id"],
                "gen.": b["generation"],
                "id": b["id"],
                "parent": b["parent"],
                "file": Path(b["file"]).name,
                "evo?": b["evolution"],
                "matches": b["stats"].get("matches", "-") or 0,
                "fitness": b["fitness"],
                "wins": b["stats"].get("wins", "-") or 0,
                "kills": b["stats"].get("enemy_kills", "-") or 0,
                "draws": b["stats"].get("draws", "-") or 0,
                "defeats": b["stats"].get("defeats", "-") or 0,
                "genome": str(b["genome"])[:30],
            })
        rows.sort(key=lambda r: r["fitness"], reverse=True)
        print(tabulate.tabulate(rows, headers="keys", tablefmt="presto") + "\n")

