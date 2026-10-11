"""Streamlit Community Cloud root entrypoint for IO Signal Sudoku."""

from pathlib import Path
import sys

# Ensure repository root is on sys.path for absolute imports
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.ui.app import main

if __name__ == "__main__":
    main()
