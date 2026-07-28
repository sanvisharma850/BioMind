"""
HELIX Agent — Molecular Analyst
Owner: Member A

Job: given LEXIS's protein list, find approved drugs that hit those
proteins (the second hop in the reasoning chain), using cached
ChEMBL/DrugBank-style data.

Note this agent does NOT need the LLM to "discover" anything — the
drug-target relationship is a lookup, not a generation task. The LLM's
job here is narrower: turn a structured match into a clean mechanism
sentence. Keeping the LLM's role small at this step reduces hallucination
risk exactly where a wrong drug-target claim would be most damaging
(SHIELD and ORACLE downstream trust this output as ground truth).
"""

import json
import os

# ---------------------------------------------------------------------------
# 1. PROMPT TEMPLATE
# ---------------------------------------------------------------------------
# This prompt is deliberately narrow: it does NOT ask the model to decide
# which drugs target which proteins (that's a lookup against real data,
# handled in match_drugs_to_proteins() below). It only asks the model to
# phrase the mechanism explanation for a match that's already verified.
# This is the key design choice that keeps HELIX honest.

HELIX_SYSTEM_PROMPT = """You are HELIX, a molecular analyst agent.
You are given a VERIFIED protein-drug match (already confirmed against
ChEMBL/DrugBank data — you are not deciding whether the match is real).

Your only job: write a SHORT (max 12 words) mechanism explanation of why
this drug is relevant to this protein, suitable for a researcher reading
a hypothesis report.

Rules:
- Do not claim the drug treats the target disease. You are only
  explaining the drug-protein mechanism, not the disease connection —
  that synthesis happens later, in ORACLE/SYNAPSE.
- Keep it under 12 words. It gets embedded mid-sentence in the final
  reasoning chain (see reasoning_chain.py), so a long or disease-mentioning
  sentence here will make that final sentence read as redundant or run-on.
- Do not invent pharmacological details not given in the input.
- Output ONLY valid JSON, no preamble.

Output schema:
{"mechanism_sentence": "<one sentence>"}
"""

HELIX_USER_PROMPT_TEMPLATE = """Protein: {protein}
Drug: {drug_name}
Approved indication: {approved_indication}
Known mechanism (raw data): {mechanism}

Write the mechanism_sentence per the schema above."""


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """Same pattern as lexis_agent.call_llm — wire this to your WatsonX client."""
    raise NotImplementedError(
        "Wire this up to your WatsonX/Granite client (same client as LEXIS)."
    )


def match_drugs_to_proteins(proteins: list[str], drug_mapping_data: dict) -> list[dict]:
    """
    Pure lookup — no LLM involved. Matches LEXIS's protein list against
    the cached ChEMBL/DrugBank-style data. This is the ground truth that
    HELIX's LLM call is not allowed to override.
    """
    matches = []
    for entry in drug_mapping_data["proteins_of_interest"]:
        protein_name = entry["protein"]
        # loose match: does the LEXIS protein string appear in/match this entry
        if any(protein_name.split()[0] in p or p.split()[0] in protein_name for p in proteins):
            for drug in entry["approved_drugs_targeting_protein"]:
                if drug.get("drug_name") and drug.get("chembl_id"):
                    matches.append({
                        "protein": protein_name,
                        "drug_name": drug["drug_name"],
                        "chembl_id": drug["chembl_id"],
                        "approved_indication": drug["approved_indication"],
                        "raw_mechanism": drug["mechanism"],
                        "known_safety_flags": drug["known_safety_flags"],
                    })
    return matches


def run_helix(proteins: list[str], drug_mapping_data: dict, llm_call=call_llm) -> list[dict]:
    matches = match_drugs_to_proteins(proteins, drug_mapping_data)
    enriched = []
    for m in matches:
        user_prompt = HELIX_USER_PROMPT_TEMPLATE.format(
            protein=m["protein"],
            drug_name=m["drug_name"],
            approved_indication=m["approved_indication"],
            mechanism=m["raw_mechanism"],
        )
        raw_output = llm_call(HELIX_SYSTEM_PROMPT, user_prompt)
        mechanism_sentence = json.loads(raw_output)["mechanism_sentence"]
        enriched.append({**m, "mechanism_sentence": mechanism_sentence})
    return enriched


# ---------------------------------------------------------------------------
# 2. FALLBACK / DEMO MODE
# ---------------------------------------------------------------------------
HELIX_DEMO_OUTPUT_ALS = [
    {
        "protein": "PRKAA1 (AMPK alpha-1 subunit)",
        "drug_name": "Metformin",
        "chembl_id": "CHEMBL1431",
        "approved_indication": "Type 2 diabetes mellitus",
        "raw_mechanism": (
            "Indirect AMPK-pathway activation associated with altered cellular "
            "energy status following inhibition of mitochondrial respiration"
        ),
        "known_safety_flags": (
            "none under standard prescribing conditions; contraindicated in "
            "severe renal impairment"
        ),
        "mechanism_sentence": "Indirectly activates AMPK by altering cellular energy status."
    }
]


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "cached_data", "als_drug_mapping.json")) as f:
        drug_data = json.load(f)

    def fake_llm_call(system_prompt, user_prompt):
        return json.dumps({"mechanism_sentence": HELIX_DEMO_OUTPUT_ALS[0]["mechanism_sentence"]})

    result = run_helix(["TARDBP (TDP-43)", "PRKAA1 (AMPK alpha-1)"], drug_data, llm_call=fake_llm_call)
    print(json.dumps(result, indent=2))
