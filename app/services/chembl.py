from app.services.cache import load_json


def get_targets(disease: str):
    return load_json(
        "chembl",
        disease
    )