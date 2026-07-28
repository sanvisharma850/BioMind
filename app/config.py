from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = f"sqlite:///{BASE_DIR}/database.db"

PROJECT_NAME = "BioMind Backend"

VERSION = "1.0.0"