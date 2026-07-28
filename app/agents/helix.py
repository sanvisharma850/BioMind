from app.services import chembl
from app.utils.timer import timed

@timed
def helix_node(state):

    disease = state["disease"]

    proteins = state["lexis"]["proteins"]

    print("LLM proteins:")
    print(proteins)

    mappings = chembl.get_targets(disease)

    print("CHEMBL mappings:")
    print(mappings)

    drugs = []

    for mapping in mappings:

        if mapping["protein"] in proteins:

            drugs.append(mapping)

    print("Matched drugs:")
    print(drugs)

    return {
        "helix": {
            "drugs": drugs
        }
    }