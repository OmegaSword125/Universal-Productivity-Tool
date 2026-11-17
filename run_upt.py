"""Run from an extracted source tree without installing the UPT package itself."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from upt.app import main

if __name__ == "__main__":
    raise SystemExit(main())
