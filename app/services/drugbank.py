from app.services.cache import load_json


def get_drugs(disease: str):
    try:
        return load_json("drugbank", disease)
    except FileNotFoundError:
        return []