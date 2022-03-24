import time
import argparse
from pathlib import Path
import subprocess
from typing import List

from tqdm import tqdm

from src.simulator import Simulator


def parse_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "bot", type=str,
        help="path to bot file",
    )

    return vars(parser.parse_args())


def main(
        bot: str,
):
    IMPORT_LINE = "from src.bots.botbase import *"

    fn = Path(bot)
    if not fn.exists():
        fn = Path(f"src/bots/{fn}")
    if not fn.exists():
        fn = Path(f"{fn}.py")
    if not fn.exists():
        print(f"Could not find bot '{bot}'")
        exit(1)

    source = fn.read_text()
    if IMPORT_LINE in source:
        botbase_file = Path(__file__).resolve().parent / "src" / "bots" / "botbase.py"
        source = "\n".join((
            source[:source.index(IMPORT_LINE)],
            f"# GameBase from commit {get_commit_hash(botbase_file)}\n\n"
            f"{botbase_file.read_text()}\n\n# ---- the actual bot ----\n\n",
            source[source.index(IMPORT_LINE) + len(IMPORT_LINE) + 1:],
        ))

    print(source)


def get_commit_hash(*files: str) -> str:
    """
    Return current commit hash

    or sequence of zeros if no git or repo is available
    """
    args = ["git", "rev-list", "--branches", "--max-count=1"]
    if files:
        args += ["--"] + [str(f) for f in files]
    try:
        return subprocess.check_output(args, cwd=Path(__file__).parent).strip().decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        return "0" * 40


if __name__ == "__main__":
    main(**parse_args())
