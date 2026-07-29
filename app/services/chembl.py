from app.services.cache import load_json


def get_targets(disease: str):
    try:
        return load_json("chembl", disease)
    except FileNotFoundError:
        return []