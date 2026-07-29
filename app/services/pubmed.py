from app.services.cache import load_json


def get_papers(disease: str):
    try:
        return load_json("pubmed", disease)
    except FileNotFoundError:
        return []