"""
pipeline_demo.py
Owner: Member A (integration handoff to Member B)

This is the piece that was MISSING before: it actually chains LEXIS's
real output into HELIX, instead of each agent's __main__ block running
its own hand-typed demo input in isolation.

Member B: this file is your starting point for SYNAPSE/LangGraph wiring.
Everything under "STUB — Member B owns this" is a deliberately minimal
placeholder for SHIELD (safety screening) and ORACLE (confidence scoring)
so the pipeline runs end-to-end today. Replace those two functions with
the real versions from your side — the rest of the chain (LEXIS -> HELIX
-> reasoning chain) does not need to change when you do.
"""

import json
import os

from lexis_agent import run_lexis, LEXIS_DEMO_OUTPUT_ALS
from helix_agent import run_helix, HELIX_DEMO_OUTPUT_ALS
from reasoning_chain import generate_reasoning_chain


# ---------------------------------------------------------------------------
# STUB — Member B owns this (SHIELD)
# ---------------------------------------------------------------------------
def stub_shield_screen(candidate: dict) -> str:
    """
    Minimal safety classifier so the pipeline runs today.
    Replace with the real SHIELD agent (Algorithm 3 in the README):
    should look up the drug in an actual FAERS-derived cache and return
    CLEAR / CAUTION / FLAGGED based on real safety records, not this
    keyword check.
    """
    flags = (candidate.get("known_safety_flags") or "").lower()
    if "black-box" in flags or "boxed warning" in flags:
        return "FLAGGED"
    if "contraindicated" in flags:
        return "CAUTION"
    return "CLEAR"


# ---------------------------------------------------------------------------
# STUB — Member B owns this (ORACLE)
# ---------------------------------------------------------------------------
def stub_oracle_score(citation_count: int, pathway_relevance: float, safety_status: str) -> float:
    """
    Minimal version of Algorithm 4 from the README. Returns a raw 0.0-1.0
    score, used ONLY for ranking candidates against each other — it is
    NOT shown to the user as a percentage (see reasoning_chain.py's
    score_to_tier for why: a hand-weighted formula is not a validated
    probability, so presenting it as "Confidence: X%" is misleading).
    Replace with the real ORACLE agent; keep weights configurable.
    """
    CITATION_CAP = 3
    w1, w2, w3 = 0.4, 0.4, 0.5
    safety_penalty = {"CLEAR": 0.0, "CAUTION": 0.3, "FLAGGED": 1.0}[safety_status]

    norm_citations = min(citation_count / CITATION_CAP, 1.0)
    score = w1 * norm_citations + w2 * pathway_relevance - w3 * safety_penalty
    return max(0.0, min(1.0, score))


# ---------------------------------------------------------------------------
# The actual chain
# ---------------------------------------------------------------------------
def run_pipeline(disease: str, papers: list[dict], drug_mapping_data: dict,
                  lexis_llm_call=None, helix_llm_call=None) -> list[dict]:
    """
    Full LEXIS -> HELIX -> SHIELD(stub) -> ORACLE(stub) -> SYNAPSE chain.

    lexis_llm_call / helix_llm_call: pass real WatsonX-backed functions
    once wired up. If left as None, falls back to the hardcoded demo
    outputs (safe for testing/recording without a live model call).
    """
    # --- LEXIS ---
    if lexis_llm_call is not None:
        lexis_output = run_lexis(disease, papers, llm_call=lexis_llm_call)
    else:
        lexis_output = LEXIS_DEMO_OUTPUT_ALS  # fallback, no live call needed

    proteins = [p["protein"] for p in lexis_output["pathways"]]
    # track which pathway each protein belongs to + how many citations, so
    # ORACLE's pathway_relevance / citation_count inputs come from LEXIS's
    # real output, not a hardcoded number
    protein_meta = {
        p["protein"]: {
            "pathway_name": p["pathway_name"],
            "citation_count": len(p["supporting_pmids"]),
            "supporting_pmids": p["supporting_pmids"],
            # first pathway in the list is treated as primary (matches
            # README Sec 4.4 definition of PathwayRelevance)
            "pathway_relevance": 1.0 if p is lexis_output["pathways"][0] else 0.5,
        }
        for p in lexis_output["pathways"]
    }

    # --- HELIX ---
    if helix_llm_call is not None:
        helix_output = run_helix(proteins, drug_mapping_data, llm_call=helix_llm_call)
    else:
        helix_output = HELIX_DEMO_OUTPUT_ALS  # fallback

    # --- SHIELD (stub) + ORACLE (stub) + SYNAPSE ---
    report = []
    for candidate in helix_output:
        meta = protein_meta.get(candidate["protein"], {
            "pathway_name": "unknown", "citation_count": 1,
            "supporting_pmids": [], "pathway_relevance": 0.5,
        })

        safety_status = stub_shield_screen(candidate)
        underlying_score = stub_oracle_score(
            citation_count=meta["citation_count"],
            pathway_relevance=meta["pathway_relevance"],
            safety_status=safety_status,
        )

        raw_flags = candidate.get("known_safety_flags", "") or ""
        if safety_status == "CLEAR":
            safety_flags_text = "none (standard dosing)"
        else:
            # raw_flags is free text like "none (standard dosing); contraindicated
            # in severe renal impairment" — surface only the clause that actually
            # triggered CAUTION/FLAGGED instead of the whole string (which starts
            # with a misleading "none").
            clauses = [c.strip() for c in raw_flags.split(";")]
            relevant = [c for c in clauses if "contraindicat" in c.lower() or "black-box" in c.lower() or "boxed warning" in c.lower()]
            safety_flags_text = "; ".join(relevant) if relevant else raw_flags

        chain_result = generate_reasoning_chain(
            drug_name=candidate["drug_name"],
            mechanism_sentence=candidate["mechanism_sentence"],
            pathway_name=meta["pathway_name"],
            disease=disease,
            supporting_pmids=meta["supporting_pmids"],
            safety_flags=safety_flags_text,
            safety_status=safety_status,
            underlying_score_0_to_1=underlying_score,
            pathway_relevance=meta["pathway_relevance"],
        )

        report.append({
            "drug_name": candidate["drug_name"],
            "protein": candidate["protein"],
            "pathway_name": meta["pathway_name"],
            "safety_status": safety_status,
            "evidence_tier": chain_result["evidence_tier"],
            "underlying_score_0_to_1": chain_result["underlying_score_0_to_1"],
            "reasoning_chain_text": chain_result["reasoning_chain_text"],
        })

    # SYNAPSE: rank by underlying score, descending (score is used for
    # sorting only — the tier + breakdown is what's actually shown to users)
    report.sort(key=lambda x: x["underlying_score_0_to_1"], reverse=True)
    return report


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    with open(os.path.join(here, "cached_data", "als_literature.json")) as f:
        lit_data = json.load(f)
    with open(os.path.join(here, "cached_data", "als_drug_mapping.json")) as f:
        drug_data = json.load(f)

    final_report = run_pipeline(
        disease=lit_data["disease"],
        papers=lit_data["papers"],
        drug_mapping_data=drug_data,
    )
    print(json.dumps(final_report, indent=2))
