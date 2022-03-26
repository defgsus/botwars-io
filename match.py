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
    parser.add_argument(
        "-sf", "--spawn-frames", type=int, nargs="?", default=10,
        help="Number of frames between spawn of new robots",
    )
    parser.add_argument(
        "-d", "--delay", type=int, nargs="?", default=100,
        help="Number of milliseconds to display each frame",
    )
    parser.add_argument(
        "-r", "--random", type=float, nargs="?", default=0.,
        help="Probability [0,1] of a bot making a random move instead of it's desired action",
    )

    return vars(parser.parse_args())


def run_games(
        filenames: List[Path],
        process_index: int,
        count: int,
        sim_params: dict,
) -> dict:

    stats = {
        "wins": [0, 0],
        "draws": [0, 0],
        "bots_alive": [0, 0],
    }
    A, B = 0, 1
    for i in tqdm(range(count), position=process_index):
        if i % 2 == 1:
            filenames = list(reversed(filenames))
            A, B = B, A

        sim = Simulator(*filenames, **sim_params)
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

        stats["bots_alive"][A] += n1
        stats["bots_alive"][B] += n2

        for key, values in sim.stats.items():
            if key not in stats:
                stats[key] = [0, 0]
            for i, v in enumerate([values[A], values[B]]):
                stats[key][i] += v

    return stats


def print_stats(stats: dict):
    for key, values in stats.items():
        print(
            f"{key:20}: "
            + " ".join(
                f"{Simulator.COLOR1 if i == 0 else Simulator.COLOR2}{v:7}{Simulator.COLOR_OFF}"
                for i, v in enumerate(values)
            )
        )


def main(
        bots: List[str],
        many: int,
        spawn_frames: int,
        delay: int,
        random: float,
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

    sim_params = {
        "spawn_frame_interval": spawn_frames,
        "random_probability": random,
    }

    bot_modules = Simulator(*filenames, **sim_params).bot_modules
    for name, fn, m in zip(("a", "b"), filenames, bot_modules):
        print(f"{name}: {fn} ({'module' if m else 'file'})")

    if not many:
        sim = Simulator(*filenames, **sim_params)
        for _ in range(100):
            sim.step()
            sim.print()
            time.sleep(delay / 1000)

        print_stats(sim.stats)

    else:
        processes = [
            (filenames, i, many // 8, sim_params)
            for i in range(8)
        ]
        results = Pool(len(processes)).starmap(run_games, processes)

        result_sum = dict()
        for r in results:
            for key, values in r.items():
                if key not in result_sum:
                    result_sum[key] = values.copy()
                else:
                    for i, v in enumerate(values):
                        result_sum[key][i] += v

        print_stats(result_sum)


if __name__ == "__main__":
    main(**parse_args())
