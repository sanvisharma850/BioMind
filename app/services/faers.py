from app.services.cache import load_json


def get_safety(disease: str):
    try:
        return load_json("faers", disease)
    except FileNotFoundError:
        return []