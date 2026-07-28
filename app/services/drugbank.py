from app.services.cache import load_json


def get_drugs(disease: str):
    return load_json(
        "drugbank",
        disease
    )