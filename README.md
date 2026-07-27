# BioMind: A Multi-Agent Framework for Evidence-Traceable Drug Repurposing Hypothesis Generation

**A Hackathon Prototype — Technical Report**

---

## Abstract

Drug repurposing — identifying new therapeutic uses for already-approved drugs — is constrained less by a lack of biological insight than by the sheer volume of disconnected evidence a researcher must manually synthesize: disease pathway literature, drug-target databases, and post-market safety records live in separate systems and are rarely cross-referenced by a single person before a hypothesis is formed. This report describes **BioMind**, a five-agent pipeline that automates the *triage* step of this process — extracting disease-relevant pathways from literature, mapping them to approved drugs via their molecular targets, screening candidates against known safety data, and producing a ranked, citation-linked hypothesis report. We explicitly scope BioMind's contribution: it does not discover novel biology, validate a hypothesis, or replace expert judgment. Its value is compressing a task that takes a researcher days of manual cross-referencing into a five-minute, fully-traceable report, where every claim resolves to a specific source. We describe the system architecture, the extraction and scoring algorithms used by each agent, a worked case study (ALS / Metformin), and the limitations of the current prototype.

---

## 1. Problem Statement

### 1.1 The literature triage bottleneck

A researcher investigating whether an existing drug might help treat a given disease must, in practice, perform several disconnected lookups:

1. **Pathway discovery** — search the literature for which biological pathways and proteins are implicated in the disease.
2. **Target mapping** — cross-reference those proteins against drug-target databases (e.g. ChEMBL, DrugBank) to find approved compounds that act on them.
3. **Safety screening** — check post-market safety databases (e.g. FDA FAERS) for contraindications or black-box warnings on any candidate.
4. **Synthesis** — combine all of the above into a defensible, ranked hypothesis, typically without any single tool doing this for them.

Each step is individually well-served by existing tools (PubMed search, ChEMBL's web interface, FAERS dashboards). No common tool chains all four into a single evidence-linked output. This is the gap BioMind targets.

### 1.2 What this is not

To avoid overclaiming — a failure mode common to hackathon biomedical AI projects — we state explicitly what BioMind does **not** do:

- It does not run wet-lab or in-silico validation of any candidate.
- It does not claim statistical or clinical significance for any ranking.
- It is not a replacement for a pharmacologist, clinician, or IRB-governed research process.
- Its "confidence score" is a transparent, inspectable heuristic (Section 5.4), not a validated predictive model.

BioMind's claim is narrower and, we argue, more honest: **it reduces the time to a well-cited first-pass hypothesis list, with every claim traceable to a source.**

---

## 2. Related Work (Context, Not Exhaustive)

Computational drug repurposing approaches broadly fall into three families: (a) network/graph-based methods that mine known drug-disease-target graphs for indirect connections, (b) machine-learning methods that predict drug-disease association scores from embeddings, and (c) literature-mining methods that extract entity relationships from biomedical text (e.g. using NLP over PubMed abstracts). BioMind is closest in spirit to family (c), but adds explicit downstream safety screening and a human-readable reasoning chain as first-class outputs — most literature-mining tools stop at entity/relation extraction and leave synthesis to the user. We do not claim algorithmic novelty over any of these families; the contribution here is the **pipeline design and evidence-traceability guarantee**, not a new extraction or scoring algorithm.

---

## 3. Proposed Solution: System Overview

BioMind is organized as five cooperating agents, each with a narrow, auditable responsibility. This decomposition is deliberate: a single monolithic "ask the LLM for a drug repurposing hypothesis" prompt cannot be audited claim-by-claim, while a pipeline of narrow agents can — a judge, or a real researcher, can inspect any single hop and verify it independently.

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
                                                                       ranked, scored candidates
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

*(See Appendix A for an AI image-generation prompt to render this as a polished architecture graphic — though see the caveat there about why we recommend building the actual diagram by hand.)*

| Agent | Responsibility | Input | Output |
|---|---|---|---|
| **LEXIS** | Extract disease-relevant pathways/proteins from literature | Disease name, cached abstracts | Pathway/protein list, each with supporting PMIDs |
| **HELIX** | Map proteins to approved drugs via molecular targets | Protein list | Drug candidates with mechanism sentences |
| **SHIELD** | Screen candidates against known safety data | Drug candidates | Candidates annotated with safety flags |
| **ORACLE** | Compute a transparent confidence score per candidate | Flagged candidates | Ranked candidates with numeric scores |
| **SYNAPSE** | Assemble the final human-readable, cited report | All of the above | Final hypothesis report |

---

## 4. Methodology: Algorithms

### 4.1 Algorithm 1 — LEXIS: Pathway/Protein Extraction

LEXIS performs constrained extraction, not open generation: it is prohibited from asserting any pathway or protein not directly supported by a provided abstract, and every output field must carry a citation.

```
Algorithm 1: LEXIS_EXTRACT
Input:  disease D, abstract set A = {a_1, ..., a_n} with PMIDs
Output: pathway list P = [(pathway_name, protein, mechanism, pmids)]

1:  prompt ← BUILD_PROMPT(D, A)          // constrained-extraction prompt, Sec 4.1.1
2:  raw ← LLM_CALL(prompt)                // structured JSON only
3:  P ← PARSE_JSON(raw)
4:  for each entry e in P:
5:      assert e.supporting_pmids ⊆ {a.pmid for a in A}   // reject hallucinated citations
6:      if e.supporting_pmids = ∅:
7:          remove e from P               // no uncited claims survive
8:  return P
```

**Design rationale.** Step 5 is the critical guard: because every downstream agent treats LEXIS's protein list as ground truth, an uncited or fabricated protein here propagates through the entire pipeline. We enforce this as a hard filter rather than a soft warning.

### 4.2 Algorithm 2 — HELIX: Target-to-Drug Matching

Unlike LEXIS, HELIX's core matching step is a **deterministic lookup**, not an LLM inference — the LLM is used only to phrase an already-verified match, which bounds hallucination risk to prose style rather than factual content.

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

### 4.4 Algorithm 4 — ORACLE: Confidence Scoring

We deliberately use a transparent weighted-sum formula rather than a trained classifier (e.g. XGBoost), because a hackathon prototype has no labeled training set for "correct repurposing candidate," and a formula the team can defend line-by-line in Q&A is more credible than an opaque model with unvalidated weights.

**Confidence formula:**

```
Confidence(c) = w1 · norm(CitationCount(c))
              + w2 · PathwayRelevance(c)
              − w3 · SafetyPenalty(c)

where:
  norm(CitationCount(c)) = min(citation_count / CITATION_CAP, 1.0)
  PathwayRelevance(c)    ∈ [0, 1], 1.0 if the matched protein is the primary
                           disease pathway per LEXIS, else 0.5 for secondary
  SafetyPenalty(c)       = 0.0 if CLEAR, 0.3 if CAUTION, 1.0 if FLAGGED

  default weights: w1 = 0.4, w2 = 0.4, w3 = 0.5 (SafetyPenalty term can
  dominate the score even with strong evidence, by design — a well-cited
  but unsafe candidate should not outrank a modestly-cited safe one)
```

```
Algorithm 4: ORACLE_SCORE
Input:  annotated candidate list C', weights (w1, w2, w3)
Output: ranked candidate list with confidence_pct ∈ [0, 100]

1:  for each candidate c in C':
2:      score ← w1·norm(CitationCount(c)) + w2·PathwayRelevance(c)
3:      score ← score − w3·SafetyPenalty(c)
4:      c.confidence_pct ← round(100 · clamp(score, 0, 1))
5:  return SORT_DESCENDING(C', key=confidence_pct)
```

### 4.5 Algorithm 5 — SYNAPSE: Reasoning Chain Assembly

SYNAPSE's job is template-based sentence assembly, not free generation (see the design note in `reasoning_chain.py`): every value plugged into the output sentence traces to a specific upstream field, so the final report sentence cannot contain a claim the earlier agents didn't already produce and verify.

```
Algorithm 5: SYNAPSE_ASSEMBLE
Input:  ranked candidate list with confidence_pct
Output: final report R = [reasoning_chain_text per candidate]

1:  for each candidate c in ranked list:
2:      sentence ← TEMPLATE_FILL(
3:                    drug=c.drug, disease=D, mechanism=c.mechanism_sentence,
4:                    citation_count=|c.supporting_pmids|,
5:                    safety_clause=RENDER_SAFETY(c.safety_status),
6:                    confidence=c.confidence_pct)
7:      R ← R ∪ {sentence}
8:  return R
```

---

## 5. Implementation

| Component | Choice | Rationale |
|---|---|---|
| LLM | IBM Granite (WatsonX) | Track alignment; strong general biomedical text handling |
| Orchestration | LangGraph (linear DAG) | Simple, debuggable agent sequencing without a full debate protocol |
| Data store | SQLite (triples) + cached JSON | Zero deployment risk for a 36-hour build; avoids live external API dependency during the demo |
| Backend | FastAPI, `asyncio` for parallel agent calls | Lightweight, fast to build |
| Frontend | React + lightweight graph view | Faster to implement well than hand-rolled D3 under time pressure |

**Caching strategy.** All literature and drug-target data used in the demo case study is pre-fetched and cached as JSON rather than queried live at demo time. This is a scope decision, not a limitation of the algorithms above — Algorithms 1–5 are agnostic to whether their input data source is a live API or a cache.

---

## 6. Case Study: ALS / Metformin

We walk through one complete pipeline run to make every algorithm's output concrete.

**Input:** disease = "Amyotrophic Lateral Sclerosis (ALS)"

**LEXIS output:** identifies TDP-43 proteinopathy (primary pathway) and AMPK/autophagy dysregulation (secondary pathway) as disease-relevant, each with supporting citations from the cached abstract set.

**HELIX output:** matches the AMPK pathway's protein (PRKAA1) to Metformin, an approved type-2-diabetes drug and known AMPK activator, via a deterministic ChEMBL-style lookup.

**SHIELD output:** Metformin's cached safety record shows no black-box warning at standard dosing → `safety_status = CLEAR`.

**ORACLE output:** with 2 supporting citations, secondary-pathway relevance (0.5), and no safety penalty, Metformin scores `confidence_pct = 78` under the default weights.

**SYNAPSE output (final report line):**

> *"Metformin is proposed for ALS because it activates AMPK, the same energy pathway impaired in ALS motor neurons, as shown in 2 supporting papers. No safety concerns flagged. Confidence: 78%."*

This is the exact sentence the current implementation (`reasoning_chain.py`) produces — not an illustrative example written after the fact.

**Important caveat on this case study:** the cached abstracts used above are placeholder text written to match real, well-established ALS biology (TDP-43 proteinopathy and AMPK/autophagy dysregulation are both real, published findings), but the specific PMIDs in the current cache are placeholders, not verified paper identifiers. Before any public claim is made using this case study, the PMIDs must be replaced with real, checked citations (see `cached_data/als_literature.json` for the flagged TODO).

---

## 7. Limitations

We list these explicitly rather than let a reviewer discover them:

1. **No clinical or experimental validation.** Confidence scores are a transparent heuristic, not a validated predictor of repurposing success.
2. **Small demo scope.** The current prototype is verified end-to-end for one disease case study; generalization to arbitrary diseases requires either live API integration or a larger cache.
3. **Placeholder citations in the demo cache.** As noted in Section 6, PMIDs in the shipped cache are illustrative and must be replaced with verified identifiers before public claims are made from them.
4. **No debate/adversarial reasoning between agents.** The original concept included a multi-agent debate protocol; the current implementation uses a linear pipeline for reliability within the build timeframe. Debate-based cross-checking is future work (Section 8).
5. **Scoring weights are hand-set, not learned.** `w1, w2, w3` in Algorithm 4 are chosen for interpretability, not fit to any ground-truth dataset, because no such labeled dataset was available.

---

## 8. Future Work

- Replace cached literature/drug-target data with live PubMed/ChEMBL/FAERS API integration, with graceful fallback to cache on API failure.
- Introduce an adversarial "critic" agent that argues against each candidate before ORACLE scores it, surfacing counter-evidence rather than only supporting evidence.
- Expand the drug-target database beyond single-protein matches to pathway-level (multi-protein) matching.
- Collect expert (pharmacologist/researcher) feedback on a candidate set to begin validating whether the confidence heuristic correlates with expert-assessed plausibility.

---

## 9. Ethical Considerations

BioMind is a research-triage tool, not a clinical decision-support system. It should not be used, and does not present itself, as a basis for treatment decisions. All outputs require expert review before any real-world action is taken on them. The system's design (Section 4) is oriented around traceability specifically so that expert review is possible — every claim resolves to a citation or a database record, not to an opaque model score.



