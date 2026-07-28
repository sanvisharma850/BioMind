from pathlib import Path
import json


CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def load_json(folder: str, filename: str):
    path = CACHE_DIR / folder / f"{filename}.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Cache not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)