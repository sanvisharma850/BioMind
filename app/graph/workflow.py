from langgraph.graph import StateGraph

from app.graph.state import BioMindState

from app.agents.lexis import lexis_node
from app.agents.helix import helix_node
from app.agents.shield import shield_node
from app.agents.oracle import oracle_node
from app.agents.synapse import synapse_node


builder = StateGraph(BioMindState)

builder.add_node(

    "lexis",

    lexis_node,

)

builder.add_node(

    "helix",

    helix_node,

)

builder.add_node(

    "shield",

    shield_node,

)

builder.add_node(

    "oracle",

    oracle_node,

)

builder.add_node(

    "synapse",

    synapse_node,

)

builder.set_entry_point("lexis")

builder.add_edge("lexis", "helix")
builder.add_edge("helix", "shield")
builder.add_edge("shield", "oracle")
builder.add_edge("oracle", "synapse")

builder.set_finish_point(

    "synapse"

)

graph = builder.compile()