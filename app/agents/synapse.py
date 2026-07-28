from langchain_core.messages import HumanMessage

from app.llm.granite import get_llm
from app.utils.prompt_loader import load_prompt
from app.utils.timer import timed

PROMPT = load_prompt("synapse")

@timed
def synapse_node(state):

    llm = get_llm()

    response = llm.invoke([

        HumanMessage(

            content=PROMPT + "\n\n"

            + str(state["oracle"])

        )

    ])

    return {

        "report": response.content

    }