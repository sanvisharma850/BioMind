from app.services import faers
from app.utils.timer import timed

@timed
def shield_node(state):

    print("STATE:", state)
    print("HELIX:", state.get("helix"))

    disease = state["disease"]

    safety = faers.get_safety(disease)

    lookup = {

        x["drug"]: x

        for x in safety

    }

    output = []

    for drug in state["helix"]["drugs"]:

        output.append({

            **drug,

            "safety": lookup.get(drug["drug"])

        })

    return {

        "shield": output

    }