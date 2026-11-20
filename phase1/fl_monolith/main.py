"""Entry point of the monolithic application: python main.py"""

from coordinator import Coordinator
from cli import CLI


def main():
    coordinator = Coordinator()
    CLI(coordinator).run()


if __name__ == "__main__":
    main()
