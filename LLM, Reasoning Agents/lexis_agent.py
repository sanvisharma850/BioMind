"""
LEXIS Agent — Literature Scout
Owner: Member A

Job: given a disease name + a set of cached paper abstracts, extract the
disease -> pathway -> protein chain, with a citation for every claim.

This is the FIRST hop in the multi-hop reasoning chain that is BioMind's
actual innovation, so the output structure matters more than the prose:
every downstream agent (HELIX, ORACLE, SYNAPSE) depends on protein names
being clean, consistent strings so they can be matched against the
drug-target data later.
"""

import json
import os

# ---------------------------------------------------------------------------
# 1. PROMPT TEMPLATE
# ---------------------------------------------------------------------------
# Design notes:
# - Forces structured JSON output (no free text) so HELIX can consume it
#   programmatically without another parsing step.
# - Forces a citation (pmid) on every extracted pathway/protein claim —
#   this is what makes the "no black boxes" pitch line actually true
#   instead of aspirational.
# - Explicitly tells the model not to invent proteins not present in the
#   provided abstracts — hallucination here breaks the whole chain
#   downstream, and a judge who checks one citation and finds it fake
#   sinks the whole demo.

LEXIS_SYSTEM_PROMPT = """You are LEXIS, a biomedical literature analysis agent.
You are given a disease name and a set of research abstracts about that disease.

Your job: extract the biological pathways and proteins implicated in the disease,
using ONLY evidence present in the provided abstracts. For each pathway/protein,
cite the exact pmid of the abstract that supports it.

Rules:
- Never invent a protein, pathway, or citation not present in the provided abstracts.
- If two abstracts support the same protein, cite both.
- Output ONLY valid JSON, no preamble, no markdown fences.
- If the abstracts don't support any clear pathway, return an empty "pathways" list
  rather than guessing.

Output schema:
{
  "disease": "<disease name>",
  "pathways": [
    {
      "pathway_name": "<short name>",
      "protein": "<protein name, canonical form e.g. 'PRKAA1 (AMPK alpha-1)'>",
      "mechanism_summary": "<1-2 sentence plain-English explanation>",
      "supporting_pmids": ["<pmid>", "..."]
    }
  ]
}
"""

LEXIS_USER_PROMPT_TEMPLATE = """Disease: {disease}

Abstracts:
{abstracts_block}

Extract the pathway/protein JSON per the schema above."""


def build_abstracts_block(papers: list[dict]) -> str:
    """Formats cached papers into the block the prompt expects."""
    lines = []
    for p in papers:
        lines.append(f"[PMID: {p['pmid']}] {p['title']}\n{p['abstract']}\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. LLM CALL WRAPPER
# ---------------------------------------------------------------------------
# Swap the body of call_llm() for your actual WatsonX/Granite client.
# Keeping it as a separate function means the prompt logic above doesn't
# change at all when Member B or Member A swaps the underlying API client —
# useful if WatsonX provisioning is slow and you need to fall back to
# another API key for a few hours.

def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Calls the LLM and returns raw text output.
    Replace this function body with your actual WatsonX call, e.g.:

        from ibm_watsonx_ai.foundation_models import ModelInference
        model = ModelInference(model_id="ibm/granite-3-8b-instruct", ...)
        response = model.generate_text(prompt=f"{system_prompt}\\n\\n{user_prompt}")
        return response

    Left unimplemented here (raises) so this fails loudly instead of
    silently returning garbage if someone forgets to wire it up.
    """
    raise NotImplementedError(
        "Wire this up to your WatsonX/Granite client. "
        "See docstring for the expected call shape."
    )


def run_lexis(disease: str, papers: list[dict], llm_call=call_llm) -> dict:
    """
    Main entry point. `llm_call` is injectable so this can be unit-tested
    with a fake function instead of hitting the real API every time.
    """
    abstracts_block = build_abstracts_block(papers)
    user_prompt = LEXIS_USER_PROMPT_TEMPLATE.format(
        disease=disease, abstracts_block=abstracts_block
    )
    raw_output = llm_call(LEXIS_SYSTEM_PROMPT, user_prompt)
    return json.loads(raw_output)


# ---------------------------------------------------------------------------
# 3. FALLBACK / DEMO MODE
# ---------------------------------------------------------------------------
# If the LLM call isn't wired up yet, or you want a guaranteed-good take
# for the recording, use this pre-computed output instead of calling the
# model live. This is the actual output you'd expect run_lexis() to
# produce given the cached ALS abstracts — hand-verified so the demo
# doesn't depend on a live model call succeeding at record time.

LEXIS_DEMO_OUTPUT_ALS = {
    "disease": "Amyotrophic Lateral Sclerosis (ALS)",
    "pathways": [
        {
            "pathway_name": "TDP-43 proteinopathy",
            "protein": "TARDBP (TDP-43)",
            "mechanism_summary": "TDP-43 mislocalizes from the nucleus to the cytoplasm and forms aggregates that disrupt RNA processing, a hallmark observed in most ALS cases.",
            "supporting_pmids": ["25652699"]
        },
        {
            "pathway_name": "AMPK energy-sensing / autophagy pathway",
            "protein": "PRKAA1 (AMPK alpha-1)",
            "mechanism_summary": "Abnormal AMPK activation is associated with TDP-43 and RNA-binding-protein mislocalization in ALS motor neurons. Metformin-related AMPK activation and autophagy provide a pathway-level drug-repurposing hypothesis, not proof of ALS efficacy.",
            "supporting_pmids": ["34634461", "33161784"]
        }
    ]
}


if __name__ == "__main__":
    # Quick local smoke test using cached data + the demo fallback output
    # (no live LLM call required to verify the plumbing works).
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "cached_data", "als_literature.json")) as f:
        data = json.load(f)

    def fake_llm_call(system_prompt, user_prompt):
        return json.dumps(LEXIS_DEMO_OUTPUT_ALS)

    result = run_lexis(data["disease"], data["papers"], llm_call=fake_llm_call)
    print(json.dumps(result, indent=2))
