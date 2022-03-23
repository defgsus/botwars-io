import time
import argparse
from pathlib import Path
from multiprocessing import Pool
from typing import List

from tqdm import tqdm

from src.simulator import Simulator


def parse_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bots", type=str, nargs=2,
        help="path to two bot files",
    )
    parser.add_argument(
        "--many", type=int, nargs="?", default=0,
        help="Number of games to run and print results",
    )

    return vars(parser.parse_args())


def run_games(args) -> dict:
    filenames, process_index, count = args

    stats = {
        "wins": [0, 0],
        "draws": [0, 0],
        "attacks": [0, 0],
        "self_attacks": [0, 0],
    }
    A, B = 0, 1
    for i in tqdm(range(count), position=process_index):
        if i % 2 == 1:
            filenames = list(reversed(filenames))
            A, B = B, A

        sim = Simulator(*filenames)
        for _ in range(100):
            sim.step()

        n1, n2 = sim.num_bots()
        if n1 == n2:
            stats["draws"][A] += 1
            stats["draws"][B] += 1
        elif n1 > n2:
            stats["wins"][A] += 1
        else:
            stats["wins"][B] += 1

        for i, v in enumerate(sim.enemy_attacks):
            stats["attacks"][i] += v
        for i, v in enumerate(sim.friendly_attacks):
            stats["self_attacks"][i] += v

    return stats


def main(
        bots: List[str],
        many: int,
):
    filenames = []
    for org_fn in bots:
        fn = Path(org_fn)
        if not fn.exists():
            fn = Path(f"src/bots/{fn}")
        if not fn.exists():
            fn = Path(f"{fn}.py")
        if not fn.exists():
            print(f"Could not find bot '{org_fn}'")
            exit(1)
        filenames.append(fn)

    bot_modules = Simulator(*filenames).bot_modules
    for name, fn, m in zip(("a", "b"), filenames, bot_modules):
        print(f"{name}: {fn} ({'module' if m else 'file'})")

    if not many:
        sim = Simulator(*filenames)
        for _ in range(100):
            sim.step()
            sim.print()
            time.sleep(.1)

    else:
        processes = [
            (filenames, i, many // 8)
            for i in range(8)
        ]
        results = Pool(len(processes)).map(run_games, processes)
        result_sum = dict()
        for r in results:
            for key, values in r.items():
                if key not in result_sum:
                    result_sum[key] = values.copy()
                else:
                    for i, v in enumerate(values):
                        result_sum[key][i] += v

        print(result_sum)


if __name__ == "__main__":
    main(**parse_args())
