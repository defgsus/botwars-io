import time

from src.simulator import Simulator


def main():
    sim = Simulator(
        "src/bots/example.py",
        "src/bots/example.py"
    )
    for _ in range(100):
        sim.step()
        sim.print()
        time.sleep(.1)

if __name__ == "__main__":
    main()
