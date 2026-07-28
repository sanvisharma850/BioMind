from app.services.cache import load_json


def get_safety(disease: str):
    return load_json(
        "faers",
        disease
    )