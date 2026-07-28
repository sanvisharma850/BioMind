from app.utils.timer import timed

@timed
def oracle_node(state):

    ranked = []

    for drug in state["shield"]:

        score = 80

        if drug["safety"]["failed_trial"]:

            score -= 30

        if drug["safety"]["black_box_warning"]:

            score -= 20

        ranked.append({

            "drug": drug["drug"],

            "protein": drug["protein"],

            "score": score

        })

    ranked.sort(

        key=lambda x: x["score"],

        reverse=True

    )

    return {

        "oracle": ranked

    }