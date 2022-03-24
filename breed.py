import time
import os
import argparse
from pathlib import Path
from multiprocessing import Pool
from typing import List

from tqdm import tqdm

from src.simulator import Simulator
from src.pool import BotPool


def parse_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bots", type=str, nargs="+",
        help="one or more paths to bot files",
    )
    parser.add_argument(
        "-p", "--pool", type=str, nargs="?", default="default",
        help="filename of pool",
    )
    parser.add_argument(
        "-r", "--reset", type=bool, nargs="?", default=False, const=True,
        help="Reset the pool file and start anew",
    )
    parser.add_argument(
        "-s", "--pool-size", type=int, nargs="?", default=10,
        help="size of pool",
    )

    return vars(parser.parse_args())


def main(
        bots: List[str],
        pool: str,
        reset: bool,
        pool_size: int,
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

    if not pool.lower().endswith(".pkl"):
        pool += ".pkl"
    pool_filename = Path(pool)
    if not pool_filename.is_absolute():
        pool_filename = Path(__file__).resolve().parent / "pools" / pool_filename

    if pool_filename.exists() and not reset:
        print("loading", pool_filename)
        pool = BotPool.load(pool_filename)
        pool.dump_population()
    else:
        pool = BotPool()

        pool.add_bot_file(*(filenames * 10))
        pool.dump_files()

        pool.create_population(count=pool_size)
        pool.evaluate()
        pool.dump_population()

    for i in range(100):
        pool.select_population(count=pool_size)
        pool.evaluate()
        pool.dump_population()
        print("top genome:", sorted(pool.population.values(), key=lambda p: p["fitness"])[-1]["genome"])

        print("saving", pool_filename)
        os.makedirs(pool_filename.parent, exist_ok=True)
        pool.save(pool_filename)


if __name__ == "__main__":
    main(**parse_args())
