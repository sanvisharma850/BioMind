from pathlib import Path


PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str):

    path = PROMPT_DIR / f"{name}.txt"

    with open(path, "r", encoding="utf-8") as f:
        return f.read()