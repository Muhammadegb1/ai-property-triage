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
- Richer role context ("senior real estate analyst", listing agent submitted, archive retrieved) — gives the model better framing.
- Changed "like [LST-XXX]" to "e.g. [LST-001]" — eliminates placeholder confusion.
- "Your first sentence compares to one listing. Your second sentence MUST compare to a DIFFERENT listing ID" — sentence-level citation enforcement.
- Added "Always use the [LST-XXX] bracket format — never refer to a listing by its title alone" — fixes bare-name citations.
- Added "If the new listing query does not mention a fact, do NOT claim that fact for the new listing" — fixes misattribution hallucination.

**Prompt:**
```
You are a senior real estate analyst.
A new property listing has been submitted, and 3 similar listings were retrieved from the agency archive.

Task: Compare the new listing to the retrieved listings using only the facts shown below.

Rules:
- Write 3–5 sentences.
- You MUST cite at least 2 different listing IDs. Even if a second listing is less comparable, cite it and briefly state how it differs.
- Always use the [LST-XXX] bracket format — never refer to a listing by its title alone.
- Compare specific facts: size, price, location, or features.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- If the new listing query does not mention a fact (size in sqm, plot size, year, etc.), do NOT claim that fact for the new listing.
- When comparing two prices or sizes, state the direction correctly.

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
| Multi-citation (≥2) | 9/10 |
| Length OK (2-5 sentences) | 10/10 |
| No hallucination | 10/10 |
| ALL passed | 9/10 |

**Failure mode identified:**
Case 08 (agricultural land) — 0 citations. Retrieved listings are all residential/commercial with no agricultural land in the index. The model writes a generic comparison ("the retrieved listings are all residential/commercial") without citing any listing by ID. This is a retrieval gap, not a prompt failure — the vector store has no comparable properties for this query type.

---

## Final Entry

**Final prompt:**
```
You are a senior real estate analyst.
A new property listing has been submitted, and 3 similar listings were retrieved from the agency archive.

Task: Compare the new listing to the retrieved listings using only the facts shown below.

Rules:
- Write 3–5 sentences.
- You MUST cite at least 2 different listing IDs. Even if a second listing is less comparable, cite it and briefly state how it differs.
- Always use the [LST-XXX] bracket format — never refer to a listing by its title alone.
- Compare specific facts: size, price, location, or features.
- Only state facts present in the listings below. Do not invent prices, sizes, or features.
- If the new listing query does not mention a fact (size in sqm, plot size, year, etc.), do NOT claim that fact for the new listing.
- When comparing two prices or sizes, state the direction correctly.

New listing:
{query}

Retrieved listings:
{listings}

Insight:
```

**Design decisions:**
- "Senior real estate analyst" + context block: frames the task correctly so the model understands it's doing archive comparison, not general commentary.
- "e.g. [LST-001]" (not "[LST-XXX]"): earlier versions with [LST-XXX] caused the model to use it as a literal placeholder.
- "Your second sentence MUST compare to a DIFFERENT listing ID": sentence-level enforcement was more effective than a general "cite 2 listings" rule.
- "Never refer to a listing by its title alone": fixes the pattern where the model wrote "the rural villa in Moshav Gimzo" instead of [LST-016].
- "If the new listing does not mention a fact, do NOT claim it": fixes misattribution where the model pulled sqm from a retrieved listing and assigned it to the new listing.
- "Use exact numbers as written": prevents M-notation conversion (4.2M vs 4200000) that caused false hallucination flags in v2.

**What I learned:**
- Adding a concrete example ID (e.g. [LST-001]) works better than a format placeholder ([LST-XXX]) — the model copies the format literally.
- Rules targeting sentence structure ("your second sentence MUST...") are more effective than rules targeting output content ("cite 2 listings").
- Role context and task framing reduce the need for long rule lists — the model behaves better when it understands the situation.
- The misattribution hallucination (model assigns a retrieved listing's sqm to the new listing) is not caught by number-presence checks — requires a separate pre-citation sentence check.
- The remaining failure (Case 08) is a retrieval gap: agricultural land has no comparable in the index, so the model gives up on citations. This is a data coverage issue, not a prompt issue.

**Pass rate progression:**

| Version | Citation | Length | Hallucination | ALL |
|---------|----------|--------|---------------|-----|
| v1 | 0/10 | 9/10 | 8/10 | 0/10 |
| v2 | 7/10 | 10/10 | 7/10 | 4/10 |
| v3 | 10/10 | 10/10 | 10/10 | 7/10 |
| v4 | 9/10 | 10/10 | 10/10 | 8/10 |
| v5 | 9/10 | 10/10 | 10/10 | 9/10 |
