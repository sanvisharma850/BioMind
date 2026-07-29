import json
from json_repair import repair_json

from langchain_core.messages import HumanMessage

from app.llm.granite import get_llm
from app.rag.retriever import retrieve_context
from app.utils.prompt_loader import load_prompt
from app.utils.timer import timed

PROMPT = load_prompt("lexis")


@timed
def lexis_node(state):

    disease = state["disease"]

    print("Disease received:", state["disease"])

    context = retrieve_context(disease)

    llm = get_llm()

    response = llm.invoke([
        HumanMessage(
            content=f"""
{PROMPT}

Disease:

{disease}

Relevant biomedical literature:

{context}
"""
        )
    ])

    print("\n========== LLM RESPONSE ==========")
    print(response.content)
    print("==================================\n")

    repaired = repair_json(response.content)
    return {
        "lexis": json.loads(repaired)
    }