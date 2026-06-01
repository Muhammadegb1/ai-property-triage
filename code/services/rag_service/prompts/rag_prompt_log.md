# Prompt Engineering Log — LangChain RAG Retrieval
# Surface #3: EC2 Service 1 — context injection and citation instructions
# Test suite: test_rag_prompt.py (10 cases, frozen before v1)

---

## Version 1 — Baseline

**Prompt:**
```
You are a real estate assistant. Write a short insight comparing the new listing to the retrieved listings.

New listing: {query}
Retrieved listings: {listings}
Insight:
```

**Results:**
| Check | Score |
|---|---|
| Citation [LST-XXX] | 0/10 |
| Length OK (1-5 sentences) | 9/10 |
| No hallucination | 8/10 |
| ALL passed | 0/10 |

**Failure mode identified:**
The model never uses `[LST-XXX]` citation format — it either writes `LST-002` without brackets or doesn't cite at all. Without citation instructions, the model also invents specific prices for retrieved listings (e.g. "LST-008 (2.45M ILS)") that do not appear in the source.

---

## Version 2 — Targeted Iteration

**Failure from v1:** No citation — model never uses `[LST-XXX]` bracket format.

**Change:** Added one rule: cite listings with exact ID in square brackets.

**Prompt:**
```
You are a real estate assistant. Write a short insight comparing the new listing to the retrieved listings.

Rules:
- Cite each retrieved listing using its exact ID in square brackets, e.g. [LST-001].

New listing: {query}
Retrieved listings: {listings}
Insight:
```

**Results:**
| Check | Score |
|---|---|
| Citation [LST-XXX] | 8/10 |
| Multi-citation (>=2) | 3/10 |
| Length OK (1-5 sentences) | 9/10 |
| No hallucination | 10/10 |
| ALL passed | 3/10 |

**Failure mode identified:**
Two distinct problems:

1. **Citation failures:** The model ignores the citation rule when no close match exists, or simply describes the new listing instead of comparing. retrieved listings were highly relevant (LST-001 for a Tel Aviv 3BR, LST-009 for an Ashdod warehouse) but the model still produced no citation.


---

## Version 3 — Targeted Iteration

**Failure from v2:** Citation skipped when no obvious match; price abbreviation causes false hallucination flags.

**Change:** Made citation a numbered mandatory requirement. Added explicit rule banning price abbreviation — model must use exact numbers as written in the source listings.

**Prompt:**
```
You are a real estate analyst. Write 2-3 sentences comparing the new listing to the most relevant retrieved listings.

Requirements — you MUST follow all of them:
1. Include at least one listing citation in the format [LST-XXX] — this is mandatory.
2. Only state facts present in the listings below. Do not invent prices, sizes, or features.
3. Use exact numbers as written in the listings. Do not convert (e.g. do not write "4.2M" if the listing says "4,200,000").

New listing:
{query}

Retrieved listings:
{listings}

Insight:
```

**Results:**
| Check | Score |
|---|---|
| Citation present | 10/10 |
| Multi-citation (≥2) | 7/10 |
| Length OK (2-5 sentences) | 10/10 |
| No hallucination | 10/10 |
| ALL passed | 7/10 |

**Failure mode identified:**
Multi-citation fails in Cases 05, 06, 07 — the model cites only 1 listing instead of 2.
- Case 07: LST-018 is nearly identical to the new listing (same building, same price) — model gets stuck on it and ignores the other two.
- Case 06: LST-001 and LST-005 are residential while the query is retail — model skips them as irrelevant instead of noting the contrast.
- Case 05: Model picks LST-002 and stops — doesn't engage with the more relevant LST-008 (same city, same bedrooms).

The rule "at least 2 different retrieved listings must be cited" is not enough — the model needs explicit guidance to cite a second listing even when it is dissimilar.

---

## Version 4 — Refinement

**Failure from v3:** Model cites only 1 listing when one retrieved listing is very similar or when the others seem irrelevant.

**Change:** Strengthened multi-citation rule — explicitly tell the model to cite a second listing even if less comparable, and state how it differs.

**Prompt:**
```
You are a real estate analyst. Write 2-3 sentences comparing the new listing to the retrieved listings.

Rules:
- Write at least 2 sentences. Each must reference at least one listing ID like [LST-XXX].
- You MUST cite at least 2 different listing IDs. Even if a second listing is less comparable, cite it and briefly state how it differs.
- Do not just describe the new listing — explain how it compares to the retrieved ones.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- Use exact numbers as written in the listings.

New listing:
{query}

Retrieved listings:
{listings}

Insight:
```

**Results:**
| Check | Score |
|---|---|
| Citation present | 9/10 |
| Multi-citation (≥2) | 8/10 |
| Length OK (2-5 sentences) | 10/10 |
| No hallucination | 10/10 |
| ALL passed | 8/10 |

**Failure mode identified:**
Two remaining failures:

1. **Case 10 — Citation 0/10 (new regression):** The model writes `[LST-XXX]` literally as a placeholder instead of using real retrieved IDs. Caused by the rule saying "like [LST-XXX]" — the model treats it as a fill-in template. Result: `[LST-XXX]` does not match `\[LST-\d+\]` so zero citations are counted.

2. **Case 03 — Multi-citation FAIL:** LST-003 is nearly identical to the new listing (same price, same type) so the model gets stuck comparing to it twice and ignores LST-016 and LST-006.

---

## Version 5 — Final Refinement

**Failure from v4:** Model uses `[LST-XXX]` as a literal placeholder; gets stuck on a single highly-similar listing.

**Change:**
- Replaced "like [LST-XXX]" with "using its exact ID (e.g. [LST-001])" — eliminates placeholder confusion.
- Added "Do not cite the same listing twice" — forces the model off a single listing.

**Prompt:**
```
You are a real estate analyst. Write 2-3 sentences comparing the new listing to the retrieved listings.

Rules:
- Write at least 2 sentences. Each must cite at least one retrieved listing using its exact ID (e.g. [LST-001]).
- You MUST cite at least 2 different listing IDs from the retrieved listings. Do not cite the same listing twice.
- Do not just describe the new listing — explain how it compares to the retrieved ones.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- Use exact numbers as written in the listings.

New listing:
{query}

Retrieved listings:
{listings}

Insight:
```

**Results:**
| Check | Score |
|---|---|
| Citation present | ?/10 |
| Multi-citation (≥2) | ?/10 |
| Length OK (2-5 sentences) | ?/10 |
| No hallucination | ?/10 |
| ALL passed | ?/10 |

---

## Final Entry

**Final prompt:** (fill — paste final prompt text)

**Design decisions:**
- (justify each line in the final prompt)

**What I learned:**
- (what phrasing patterns worked)
- (what consistently failed)

**Pass rate progression:**

| Version | Citation | Length | Hallucination | ALL |
|---------|----------|--------|---------------|-----|
| v1 | 0/10 | 9/10 | 8/10 | 0/10 |
| v2 | 7/10 | 10/10 | 7/10 | 4/10 |
| v3 | 10/10 | 10/10 | 10/10 | 7/10 |
| v4 | 9/10 | 10/10 | 10/10 | 8/10 |
| v5 | ?/10 | ?/10 | ?/10 | ?/10 |
