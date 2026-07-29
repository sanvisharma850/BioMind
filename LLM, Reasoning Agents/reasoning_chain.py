"""
Reasoning Chain Generator
Owner: Member A

This is arguably the single highest-leverage file for a video-only
submission: it's the text that appears on screen when SYNAPSE delivers
its final answer, and it's what makes the demo read as "a scientific
tool reasoned about this" rather than "a chatbot summarized something."

Do NOT let the LLM free-write this. Free-written LLM prose tends to
either (a) hedge everything into mush, or (b) overclaim ("this drug
treats ALS"). Instead, template the structure and only let the LLM fill
narrow slots — this guarantees every sentence traces back to a specific
piece of evidence, which is the whole "no black boxes" pitch.

IMPORTANT DESIGN NOTE (revised): earlier versions of this pipeline output
a raw "Confidence: 78%" number computed from a hand-weighted formula.
That's misleading — it implies a calibrated probability of success that
nothing in this system actually measures or validates. This version
replaces the bare percentage with an explicit evidence TIER (Strong /
Moderate / Weak / Not Recommended) plus a visible breakdown of exactly
what evidence produced that tier. The underlying continuous score is
still computed (see ORACLE in pipeline_demo.py) and still used for
ranking candidates against each other — it's just not shown to the user
dressed up as a statistic, because a ranking is defensible and a fake
probability is not.
"""

import json
import os


# ---------------------------------------------------------------------------
# Evidence tiers — replaces the old raw percentage
# ---------------------------------------------------------------------------
# Thresholds operate on the same 0.0-1.0 underlying score ORACLE computes
# (see pipeline_demo.py: stub_oracle_score). The tier is what's shown to
# the user; the raw score is kept internally only for sorting candidates.

def score_to_tier(score_0_to_1: float, safety_status: str) -> str:
    """
    safety_status can override the tier outright: a FLAGGED candidate is
    never presented as Strong/Moderate evidence regardless of citation
    count, because a safety flag is a reason to deprioritize, not a
    number to net against literature support.
    """
    if safety_status == "FLAGGED":
        return "Not Recommended"
    if score_0_to_1 >= 0.7:
        return "Strong"
    if score_0_to_1 >= 0.4:
        return "Moderate"
    return "Weak"


def pathway_relevance_desc(pathway_relevance: float) -> str:
    return "primary disease pathway" if pathway_relevance >= 1.0 else "secondary pathway match"


def safety_desc(safety_status: str, safety_flags: str) -> str:
    if safety_status == "CLEAR":
        return "no safety concerns flagged"
    if safety_status == "CAUTION":
        return f"safety caution: {safety_flags}"
    return f"safety flag: {safety_flags}"


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------
REASONING_CHAIN_TEMPLATE = (
    "{drug_name} — {evidence_tier} Evidence "
    "({citation_count} supporting paper{plural}, {pathway_relevance_text}, "
    "{safety_text}). "
    "Proposed for {disease} because it {mechanism_lower}."
)


def lowercase_first_letter(s: str) -> str:
    return s[0].lower() + s[1:] if s else s


def generate_reasoning_chain(
    drug_name: str,
    mechanism_sentence: str,
    pathway_name: str,
    disease: str,
    supporting_pmids: list,
    safety_flags: str,
    safety_status: str,
    underlying_score_0_to_1: float,
    pathway_relevance: float,
) -> dict:
    """
    Pure string templating — no LLM, no hallucination risk. Every value
    plugged in here should trace back to LEXIS/HELIX/SHIELD/ORACLE output,
    not be invented at this step.

    Returns a dict, not just a string, so the tier and raw score are both
    available separately (e.g. frontend can color-code by tier, and
    ranking logic can still sort by underlying_score_0_to_1 without
    displaying it).
    """
    citation_count = len(supporting_pmids)
    plural = "s" if citation_count != 1 else ""

    mech = mechanism_sentence.rstrip(".")
    if mech.lower().startswith(drug_name.lower()):
        mech = mech[len(drug_name):].lstrip()
    mech = lowercase_first_letter(mech)

    tier = score_to_tier(underlying_score_0_to_1, safety_status)

    text = REASONING_CHAIN_TEMPLATE.format(
        drug_name=drug_name,
        evidence_tier=tier,
        citation_count=citation_count,
        plural=plural,
        pathway_relevance_text=pathway_relevance_desc(pathway_relevance),
        safety_text=safety_desc(safety_status, safety_flags),
        disease=disease,
        mechanism_lower=mech,
    )

    return {
        "drug_name": drug_name,
        "evidence_tier": tier,
        "underlying_score_0_to_1": round(underlying_score_0_to_1, 3),
        "reasoning_chain_text": text,
    }


# ---------------------------------------------------------------------------
# Optional: LLM-polish pass (unchanged — still copy-editing only, never
# adds claims, so it's still safe to use with the new tier-based output)
# ---------------------------------------------------------------------------
POLISH_SYSTEM_PROMPT = """You are a scientific copy editor. You will be given a
sentence that is already factually complete and correct. Improve ONLY the
phrasing/flow. Do not add, remove, or change any factual claim, number,
drug name, protein name, tier label, or citation count. If you are not
sure a change is purely stylistic, leave that part unchanged. Output only
the revised sentence, nothing else."""


def polish_reasoning_chain(raw_sentence: str, llm_call) -> str:
    return llm_call(POLISH_SYSTEM_PROMPT, raw_sentence).strip()


# ---------------------------------------------------------------------------
# Demo output (ALS / Metformin), using the actual cached-data-derived
# values from pipeline_demo.py's real run rather than hand-typed numbers.
# ---------------------------------------------------------------------------
def build_als_demo_reasoning_chain() -> dict:
    return generate_reasoning_chain(
        drug_name="Metformin",
        mechanism_sentence=(
            "Metformin activates AMPK and autophagy pathways relevant to "
            "neuronal energy regulation and protein clearance."
        ),
        pathway_name="AMPK energy-sensing / autophagy pathway",
        disease="Amyotrophic Lateral Sclerosis (ALS)",
        supporting_pmids=["34634461", "33161784"],
        safety_flags="contraindicated in severe renal impairment",
        safety_status="CAUTION",
        underlying_score_0_to_1=0.32,
        pathway_relevance=0.5,
    )


if __name__ == "__main__":
    result = build_als_demo_reasoning_chain()
    print(json.dumps(result, indent=2))
    print()
    print("On-screen text:")
    print(result["reasoning_chain_text"])
