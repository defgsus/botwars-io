import argparse
from pathlib import Path
import subprocess
from typing import List, Optional


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
        commit_hash = get_commit_hash(botbase_file)
        if commit_hash:
            header = f"# GameBase from https://github.com/defgsus/botwars-io/blob/{commit_hash}/src/bots/botbase.py"
        else:
            header = ""
        source = "\n".join((
            source[:source.index(IMPORT_LINE)],
            f"{header}\n\n"
            f"{botbase_file.read_text()}\n\n# ---- the actual bot ----\n\n",
            source[source.index(IMPORT_LINE) + len(IMPORT_LINE) + 1:],
        ))

    print(source)


def get_commit_hash(*files: str) -> Optional[str]:
    """
    Return current commit hash
    """
    args = ["git", "rev-list", "--branches", "--max-count=1"]
    if files:
        args += ["--"] + [str(f) for f in files]
    try:
        return subprocess.check_output(args, cwd=Path(__file__).parent).strip().decode("utf-8")
    except (subprocess.CalledProcessError, UnicodeDecodeError):
        pass


if __name__ == "__main__":
    main(**parse_args())
