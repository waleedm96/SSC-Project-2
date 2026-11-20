"""
Step 6b - Entry point. Run with:  python main.py
"""

from cli import CLI
from coordinator import Coordinator


def main() -> None:
    coordinator = Coordinator()
    CLI(coordinator).run()


if __name__ == "__main__":
    main()
