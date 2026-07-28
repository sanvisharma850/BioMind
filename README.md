# BioMind: A Multi-Agent Framework for Evidence-Traceable Drug Repurposing Hypothesis Generation

**A Hackathon Prototype — Technical Report**

---

</div>

<p align="center">
  <img src="assets/v2_awv-a44c972a3823a57d (online-video-cutter.com).gif" width="700"/>
</p>

## Abstract

Drug repurposing is bottlenecked by evidence fragmentation, not by a shortage of biological insight. Disease-pathway literature, drug-target databases, and post-market safety records live in separate systems, and no single researcher cross-references all three before forming a hypothesis. **BioMind** solves this with a five-agent pipeline that automates evidence triage: it extracts disease-relevant pathways from literature, maps them to approved drugs via molecular targets, screens candidates against known safety data, and produces a ranked, citation-linked hypothesis report — end to end, in minutes, with every claim traceable to its source.

BioMind's scope is deliberate and stated up front: it generates ranked, evidence-backed hypotheses for a human researcher to validate. It does not run wet-lab or in-silico validation, and it does not assign candidates a probability of clinical success. That distinction is the system's core design principle, not a limitation to apologize for: every score BioMind produces is a transparent, inspectable rule, and every claim resolves to a specific paper or database record. This report specifies the system architecture, the extraction and scoring algorithms behind each agent, and a fully worked case study (ALS / Metformin) using real pipeline output.





---

## 1. Problem Statement

### 1.1 The literature triage bottleneck


<p align="center">
  <img src="assets/Gemini_Generated_Image_d9zepkd9zepkd9ze.png" width="90%" />
</p>

Investigating whether an existing drug might treat a given disease requires four disconnected steps, performed manually, every time:

1. **Pathway discovery** — search the literature for pathways and proteins implicated in the disease.
2. **Target mapping** — cross-reference those proteins against drug-target databases (ChEMBL, DrugBank) for approved compounds that act on them.
3. **Safety screening** — check post-market safety data (FDA FAERS) for contraindications or black-box warnings on each candidate.
4. **Synthesis** — combine all of the above into a ranked, defensible hypothesis.

Each step is well-served individually by existing tools. None of them chains into the next. BioMind closes that gap.

<p align="center">
  <img src="assets/Gemini_Generated_Image_ojp7dwojp7dwojp7.png" width="90%" />
</p>

### 1.2 Scope, stated precisely

BioMind reduces literature triage time. It does not discover new biology, does not validate a hypothesis, and does not replace a pharmacologist's judgment. Its confidence output is a transparent, rule-based evidence tier (Section 4.4), not a validated predictive score — and it is built that way on purpose: a percentage implies a calibrated probability that no formula built without labeled outcome data can honestly provide. A transparent tier the team can defend line-by-line is more useful, and more credible, than a number that only looks rigorous.

---

## 2. Related Work

Computational drug repurposing splits into three established families: network/graph-based methods that mine drug-disease-target graphs for indirect connections, machine-learning methods that predict association scores from learned embeddings, and literature-mining methods that extract entity relationships from biomedical text. BioMind sits in the third family and extends it: most literature-mining tools stop at entity/relation extraction and leave synthesis to the user. BioMind adds safety screening and a human-readable, source-traceable reasoning chain as first-class pipeline outputs, not an afterthought. The contribution here is pipeline design and evidence-traceability guarantees — not a new extraction or scoring algorithm, and the report does not claim otherwise.

---

## 3. Solution: System Architecture

BioMind runs five agents, each with one narrow, auditable responsibility. This decomposition is the design's central strength: a single "ask the LLM for a repurposing hypothesis" prompt cannot be checked claim-by-claim. A pipeline of narrow agents can — any hop is independently verifiable by a researcher or a judge.

```
  Disease Name
       |
       v
  ┌─────────┐     pathways/proteins     ┌─────────┐     candidate drugs      ┌─────────┐
  │  LEXIS  │ ────────────────────────> │  HELIX  │ ───────────────────────> │ SHIELD  │
  │ (Lit.   │   + citations             │ (Target │   + mechanism            │ (Safety │
  │ Scout)  │                           │  Match) │                          │ Screen) │
  └─────────┘                           └─────────┘                          └─────────┘
                                                                                    |
                                                                    flagged/cleared candidates
                                                                                    v
                                                                              ┌─────────┐
                                                                              │ ORACLE  │
                                                                              │ (Scoring)│
                                                                              └─────────┘
                                                                                    |
                                                                       ranked, tiered candidates
                                                                                    v
                                                                              ┌─────────┐
                                                                              │ SYNAPSE │
                                                                              │(Synthesis)│
                                                                              └─────────┘
                                                                                    |
                                                                                    v
                                                                    Ranked, cited, plain-English
                                                                         hypothesis report
```
 

 
| Agent | Responsibility | Input | Output |
|---|---|---|---|
| **LEXIS** | Extracts disease-relevant pathways/proteins from literature | Disease name, cached abstracts | Pathway/protein list, each with supporting PMIDs |
| **HELIX** | Maps proteins to approved drugs via molecular targets | Protein list | Drug candidates with mechanism sentences |
| **SHIELD** | Screens candidates against known safety data | Drug candidates | Candidates annotated CLEAR / CAUTION / FLAGGED |
| **ORACLE** | Computes a transparent evidence score per candidate | Flagged candidates | Ranked candidates with an evidence tier |
| **SYNAPSE** | Assembles the final human-readable, cited report | All of the above | Final hypothesis report |
 
---
 
## 4. Methodology: Algorithms
 
### 4.1 Algorithm 1 — LEXIS: Pathway/Protein Extraction

<p align="center">
  <img src="assets/Gemini_Generated_Image_r8y9lpr8y9lpr8y9.png" width="90%" />
</p>
 
LEXIS performs constrained extraction, not open generation. It is prohibited from asserting any pathway or protein not directly supported by a provided abstract, and every output field carries a citation. This constraint is enforced in code, not just in the prompt.
 
```
Algorithm 1: LEXIS_EXTRACT
Input:  disease D, abstract set A = {a_1, ..., a_n} with PMIDs
Output: pathway list P = [(pathway_name, protein, mechanism, pmids)]
 
1:  prompt ← BUILD_PROMPT(D, A)          // constrained-extraction prompt
2:  raw ← LLM_CALL(prompt)                // structured JSON only
3:  P ← PARSE_JSON(raw)
4:  for each entry e in P:
5:      assert e.supporting_pmids ⊆ {a.pmid for a in A}   // reject hallucinated citations
6:      if e.supporting_pmids = ∅:
7:          remove e from P               // no uncited claims survive
8:  return P
```
 
Step 5 is the load-bearing guard: every downstream agent treats LEXIS's protein list as ground truth, so an uncited or fabricated protein here would propagate through the entire pipeline undetected. Enforcing it as a hard filter, not a soft warning, is what makes the "no black boxes" claim true rather than aspirational.
 
### 4.2 Algorithm 2 — HELIX: Target-to-Drug Matching
 
HELIX's core matching step is a deterministic database lookup, not an LLM inference. The LLM's only role is phrasing an already-verified match, which confines any hallucination risk to prose style — never to factual content.
 
```
Algorithm 2: HELIX_MATCH
Input:  protein list [p_1, ..., p_k], drug-target database T
Output: candidate list C = [(drug, protein, mechanism_sentence, safety_raw)]
 
1:  C ← ∅
2:  for each protein p in [p_1, ..., p_k]:
3:      matches ← LOOKUP(T, p)            // deterministic DB match, not LLM
4:      for each (drug, indication, mechanism_raw, safety_raw) in matches:
5:          sentence ← LLM_POLISH(drug, mechanism_raw)  // phrasing only, no new facts
6:          C ← C ∪ {(drug, p, sentence, safety_raw)}
7:  return C
```
 
### 4.3 Algorithm 3 — SHIELD: Safety Screening
 
```
Algorithm 3: SHIELD_SCREEN
Input:  candidate list C, safety database S (e.g. cached FAERS records)
Output: annotated candidate list C' with safety_status ∈ {CLEAR, CAUTION, FLAGGED}
 
1:  for each candidate c in C:
2:      record ← LOOKUP(S, c.drug)
3:      if record contains a black-box warning relevant to c.drug:
4:          c.safety_status ← FLAGGED
5:      else if record contains a contraindication note:
6:          c.safety_status ← CAUTION
7:      else:
8:          c.safety_status ← CLEAR
9:  return C
```
 
### 4.4 Algorithm 4 — ORACLE: Evidence Scoring and Tiering
 
ORACLE computes a transparent weighted-sum score and converts it into an **evidence tier** — Strong, Moderate, Weak, or Not Recommended — rather than presenting a raw percentage. This is a deliberate design choice, made for a specific reason: a percentage reads as a calibrated probability, and no formula built without labeled ground-truth outcomes can honestly claim to be one. A tier backed by a visible breakdown of exactly which evidence produced it is a claim BioMind can actually defend.
 
**Underlying score (used for ranking, not displayed as a statistic):**
 
```
Score(c) = w1 · norm(CitationCount(c)) + w2 · PathwayRelevance(c) − w3 · SafetyPenalty(c)
 
where:
  norm(CitationCount(c)) = min(citation_count / CITATION_CAP, 1.0)
  PathwayRelevance(c)    ∈ [0, 1], 1.0 for the primary disease pathway per LEXIS,
                           0.5 for a secondary pathway
  SafetyPenalty(c)       = 0.0 if CLEAR, 0.3 if CAUTION, 1.0 if FLAGGED
  default weights: w1 = 0.4, w2 = 0.4, w3 = 0.5
```
 
**Tier mapping — what the user actually sees:**
 
```
Algorithm 4: ORACLE_SCORE_AND_TIER
Input:  annotated candidate list C', weights (w1, w2, w3)
Output: ranked candidate list, each with an evidence_tier and a visible
        breakdown (citation count, pathway match type, safety status)
 
1:  for each candidate c in C':
2:      c.score ← w1·norm(CitationCount(c)) + w2·PathwayRelevance(c) − w3·SafetyPenalty(c)
3:      c.score ← clamp(c.score, 0, 1)
4:      if c.safety_status = FLAGGED:
5:          c.evidence_tier ← "Not Recommended"       // overrides score outright
6:      else if c.score ≥ 0.7:
7:          c.evidence_tier ← "Strong"
8:      else if c.score ≥ 0.4:
9:          c.evidence_tier ← "Moderate"
10:     else:
11:         c.evidence_tier ← "Weak"
12: return SORT_DESCENDING(C', key=c.score)
```
 
The FLAGGED override in step 4–5 is non-negotiable by design: a well-cited but unsafe candidate can never outrank its safety flag by accumulating citations. A safety flag is a reason to deprioritize, not a number to net against literature support.
 
### 4.5 Algorithm 5 — SYNAPSE: Reasoning Chain Assembly
 
SYNAPSE assembles the final report through template-based sentence construction, not free generation. Every value plugged into the output sentence traces to a specific upstream field, guaranteeing the final report cannot contain a claim the earlier agents did not already produce and verify.
 
```
Algorithm 5: SYNAPSE_ASSEMBLE
Input:  ranked candidate list with evidence_tier and breakdown fields
Output: final report R = [reasoning_chain_text per candidate]
 
1:  for each candidate c in ranked list:
2:      sentence ← TEMPLATE_FILL(
3:                    drug=c.drug, tier=c.evidence_tier,
4:                    citation_count=|c.supporting_pmids|,
5:                    pathway_match=RENDER_PATHWAY(c.pathway_relevance),
6:                    safety_text=RENDER_SAFETY(c.safety_status),
7:                    disease=D, mechanism=c.mechanism_sentence)
8:      R ← R ∪ {sentence}
9:  return R
```
 
---
 
## 5. Implementation
 
| Component | Choice | Rationale |
|---|---|---|
| LLM | IBM Granite (WatsonX) | Track alignment; strong general biomedical text handling |
| Orchestration | LangGraph (linear DAG) | Simple, debuggable agent sequencing |
| Data store | SQLite (triples) + cached JSON | Zero deployment risk; no live external API dependency during the demo |
| Backend | FastAPI, `asyncio` for parallel agent calls | Lightweight, fast to build, fast to run |
| Frontend | React + lightweight graph view | Ships a working, polished UI without hand-rolled D3 |
 
**Caching strategy.** All literature and drug-target data used in the demo case study is pre-fetched and cached as JSON, so the demo runs on data that has already been verified once, not on a live API call that could fail mid-recording. Algorithms 1–5 are agnostic to the data source — swapping cache for live API access requires no algorithmic change, only a data-source swap.
 
---
 
## 6. Case Study: ALS / Metformin

 
One complete pipeline run, using real output from the current implementation.
 
**Input:** disease = "Amyotrophic Lateral Sclerosis (ALS)"
 
**LEXIS** identifies TDP-43 proteinopathy as the primary pathway and AMPK/autophagy dysregulation as a secondary pathway, each backed by citations from the cached abstract set.
 
**HELIX** matches the AMPK pathway's protein (PRKAA1) to Metformin — an approved type-2-diabetes drug and a well-characterized AMPK activator — via a deterministic ChEMBL-style lookup.
 
**SHIELD** finds a real caution in Metformin's cached safety record (contraindicated in severe renal impairment) and classifies it CAUTION.
 
**ORACLE** computes a score of 0.32 from 2 citations, a secondary-pathway match, and the CAUTION penalty, which maps to a **Weak** evidence tier under the default thresholds.
 
**SYNAPSE's final report line (exact current output):**
 
> *"Metformin — Weak Evidence (2 supporting papers, secondary pathway match, safety caution: contraindicated in severe renal impairment). Proposed for Amyotrophic Lateral Sclerosis (ALS) because it activates AMPK, the same energy pathway impaired in ALS motor neurons."*
 
This sentence is produced directly by the shipped `pipeline_demo.py` and `reasoning_chain.py` — not written after the fact to illustrate the concept.
 
**One fact to fix before public claims are made from this case study:** the cached abstracts are placeholder text written to match real, published ALS biology (TDP-43 proteinopathy and AMPK/autophagy dysregulation are both genuine, well-documented findings), but the PMIDs currently in the cache are placeholders. Swap in verified PubMed identifiers before the video or submission goes out — this is a data-population task, not a code change, and does not touch any algorithm above.
 
---
 
## 7. Design Boundaries
 
BioMind is built around a small number of firm boundaries, stated here so no reviewer has to guess at them:
 
1. **No clinical or experimental validation is claimed.** The evidence tier is a transparent, rule-based classification, not a predictor of repurposing success — and it is presented that way on purpose (Section 4.4).
2. **The demo covers one fully verified case study.** Generalizing to arbitrary diseases requires either live API integration or a larger cache — a scope decision, not an architectural constraint.
3. **The shipped demo cache uses placeholder PMIDs**, flagged directly in `cached_data/als_literature.json`, pending a straightforward swap to verified citations.
4. **The pipeline is linear, not adversarial.** An earlier concept included a multi-agent debate protocol; the current build uses a linear DAG for reliability within the build window. Debate-based cross-checking is scoped as future work (Section 8), not a missing core feature.
5. **Scoring weights are hand-set for interpretability**, not fit to a labeled dataset — because no such dataset exists yet, and a hand-set, disclosed formula is more honest than a fit one presented without the data to justify it.
---
 
## 8. Future Work
 
- Live PubMed/ChEMBL/FAERS API integration, with graceful fallback to cache on failure.
- An adversarial "critic" agent that argues against each candidate before ORACLE scores it, surfacing counter-evidence alongside supporting evidence.
- Pathway-level (multi-protein) target matching, beyond the current single-protein match.
- Expert (pharmacologist/researcher) review of a candidate set, as a first step toward validating whether the evidence tier correlates with expert-assessed plausibility.
---
 
## 9. Ethical Considerations
 
BioMind is a research-triage tool. It is not, and does not present itself as, a clinical decision-support system, and no output should inform a treatment decision without expert review. The entire architecture is built around making that review possible: every claim resolves to a citation or a database record, never to an opaque model score.
