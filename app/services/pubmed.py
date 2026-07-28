from app.services.cache import load_json


def get_papers(disease: str):
    return load_json(
        "pubmed",
        disease
    )