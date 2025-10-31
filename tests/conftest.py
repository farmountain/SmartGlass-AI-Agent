from pathlib import Path
import sys

# Ensure the "src" package is importable for tests that use the source layout.
ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
