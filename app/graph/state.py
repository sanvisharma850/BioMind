from typing import TypedDict


class BioMindState(TypedDict):
    disease: str

    lexis: dict
    helix: dict
    shield: dict
    oracle: list
    report: str

    status: dict
    timings: dict