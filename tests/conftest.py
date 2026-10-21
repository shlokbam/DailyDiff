import os
import sys
from pathlib import Path

# Use local SQLite for tests so tests are hermetic and don't hit remote database
os.environ["DATABASE_URL"] = ""

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(BASE_DIR / "backend") not in sys.path:
    sys.path.insert(0, str(BASE_DIR / "backend"))

