# Prompt Engineering Log — Layer 2 n8n Orchestration
# Surfaces: Node 4 (Information Extractor), Node 5 (AI Agent), Node 6 (Final Report LLM Chain)
# Models: Gemini / GPT-4o-mini (Node 4), GPT-4o (Node 5, Node 6)

---

# Surface #1 — Node 4 Information Extractor

## Test Suite (10 listing descriptions)

| # | Listing snippet | Expected highlights |
|---|---|---|
| 01 | "5-bedroom apartment, Florentin Tel Aviv, 110sqm, 500,000 ILS" | apartment, Florentin/Tel Aviv, 500000, 5 |
| 02 | "Commercial office space, Rothschild Blvd, 200sqm" | office, Rothschild, null price, null rooms |
| 03 | "Charming villa in Caesarea with pool" | villa, Caesarea, null price, null rooms |
| 04 | "2BR flat, negotiable, recently renovated kitchen" | apartment, null price, 2 |
| 05 | "Retail unit in Dizengoff Center, 80sqm" | retail, Dizengoff, null, null |
| 06 | "Industrial warehouse, Ashdod port area, 1200sqm" | industrial, Ashdod, null, null |
| 07 | "Studio in Jerusalem city centre" | apartment/other, Jerusalem, null, 1 or null |
| 08 | "House with garden, 4 rooms, Herzliya Pituach, 3.2M NIS" | house, Herzliya, 3200000, 4 |
| 09 | "Energy rating A, solar panels, 3BR Ramat Gan" | apartment, Ramat Gan, certifications="A" |
| 10 | "Hello, is anyone there?" (spam / not a listing) | other, empty fields, [] features |

---

## Version 1 — Baseline

**Prompt:** `extractor_v1.txt` — prose output, no schema.

**Results:** JSON parseable: **0/10** | Correct field types: **N/A** | No invented values: **4/10** | **ALL passed: 0/10**

**Failure:** Node 4b parser cannot process prose. Model returns paragraphs like "This is a 5-bedroom apartment located in Florentin…" instead of JSON.

---

## Version 2 — JSON with wrong keys

**Failure from v1:** Output is not JSON.

**Change:** Request JSON with keys `type, city, price, rooms, features` (wrong names).

**Prompt:** `extractor_v2.txt`

**Results:** JSON parseable: **8/10** | Correct schema keys: **0/10** | **ALL passed: 0/10**

**Failure:** Parser expects `property_type`, `location`, `price_ils` — model returns `{"type":"apartment","city":"Tel Aviv","price":"500000"}`.

---

## Version 3 — Correct keys, no null handling

**Failure from v2:** Wrong key names break downstream nodes.

**Change:** Use correct keys but require all fields as non-null values.

**Prompt:** `extractor_v3.txt`

**Results:** JSON parseable: **9/10** | Correct keys: **9/10** | No invented values: **3/10** | **ALL passed: 3/10**

**Failure:** Model invents `price_ils: 0` or `num_rooms: 3` when not stated (cases 02, 04, 07).

---

## Version 4 — Schema + nulls, markdown fences

**Failure from v3:** Model invents missing numeric fields.

**Change:** Explicit `null` for missing numbers; enum for `property_type`; "extract only stated facts."

**Prompt:** `extractor_v4.txt`

**Results:** JSON parseable: **7/10** | No invented values: **9/10** | No markdown fences: **4/10** | **ALL passed: 4/10**

**Failure:** Model wraps output in ` ```json ` fences (6/10 cases), breaking Node 4b regex parser on first attempt.

---

## Version 5 — Production

**Failure from v4:** Markdown code fences break parser.

**Change:** Explicit ban on fences; room-count normalisation rule; strict null/[] defaults.

**Prompt:** `extractor_v5.txt` (deployed in n8n Node 4)

**Results:** **10/10** — all cases parse correctly, no invented fields, no markdown wrappers.

**Deployed in:** `AI_Property_Triage_n8n.json` → Node 4 Extract listing (LLM)

---

# Surface #2 — Node 5 AI Agent

## Test Suite (10 agent runs)

| # | Scenario | Pass criteria |
|---|---|---|
| 01 | Full listing + 4 image URLs | Calls langgraph_agent exactly once |
| 02 | Listing only, no images | Calls langgraph_agent once, image_scores=[] |
| 03 | Commercial office listing | routing_decision="commercial" |
| 04 | Residential villa | routing_decision="residential" |
| 05 | Langgraph returns 3 similar listings | similar_listings has 3 entries |
| 06 | 5 image URLs submitted | image_scores has 5 entries |
| 07 | Langgraph mentions RAG error | rag_insight preserves error, not replaced |
| 08 | Missing price in extraction | price_ils=null in output |
| 09 | Agent tries to skip tool call | Must still call langgraph_agent |
| 10 | Agent outputs markdown-wrapped JSON | Raw JSON only |

---

## Version 1 — Baseline (no tools)

**Prompt:** `agent_system_v1.txt`

**Results:** Tool called: **0/10** | Valid JSON: **0/10** | **ALL passed: 0/10**

**Failure:** Plain-text summaries only. No tool invocation, no structured output for Node 6.

---

## Version 2 — Tools mentioned, no format

**Failure from v1:** Agent never calls langgraph_agent.

**Change:** Name the tool and say "use when needed."

**Prompt:** `agent_system_v2.txt`

**Results:** Tool called: **4/10** | Valid JSON: **0/10** | **ALL passed: 0/10**

**Failure:** Agent sometimes calls the tool but returns prose. Tool description too vague — agent skips RAG/image analysis for 6/10 cases.

---

## Version 3 — Tool call + partial JSON schema

**Failure from v2:** No structured output; inconsistent tool usage.

**Change:** "Call once" + list output fields.

**Prompt:** `agent_system_v3.txt`

**Results:** Tool called: **8/10** | Valid JSON: **5/10** | routing_decision correct: **6/10** | **ALL passed: 3/10**

**Failure:** JSON missing `similar_listings` structure; agent invents listing titles; `image_scores` omitted when images present.

---

## Version 4 — Full schema, cardinality not enforced

**Failure from v3:** Incomplete JSON; invented similar listings.

**Change:** Full JSON template with routing rules and anti-invention rule.

**Prompt:** `agent_system_v4.txt`

**Results:** Valid JSON: **9/10** | routing_decision: **10/10** | similar_listings count: **4/10** | image_scores count: **5/10** | **ALL passed: 4/10**

**Failure:** Agent includes only 1 similar listing when langgraph mentions 3. image_scores has 2 entries when 5 URLs submitted.

---

## Version 5 — Production

**Failure from v4:** Cardinality mismatch on similar_listings and image_scores.

**Change:** CRITICAL block enforcing N image entries and all similar listings from langgraph answer.

**Prompt:** `agent_system_v5.txt` (deployed in n8n Node 5)

**Tool description iterations (same surface):**

| Version | langgraph_agent toolDescription | Tool selected correctly |
|---|---|---|
| v1 | "Analyse property" | 3/10 |
| v2 | "Calls RAG and image services" | 5/10 |
| v3 | Added query format example | 7/10 |
| v4 | Added "send description + URLs in one query" | 9/10 |
| v5 | Full example with placeholder definitions (deployed) | **10/10** |

**Results:** **10/10**

**Deployed in:** `AI_Property_Triage_n8n.json` → Node 5 AI Agent + langgraph_agent tool node

---

# Surface #3 (Layer 2) — Node 6 Final Report LLM Chain

## Test Suite (10 normalisation cases)

| # | Input issue | Pass criteria |
|---|---|---|
| 01 | Valid complete JSON from Node 5 | Preserves all fields verbatim |
| 02 | property_type="apartment" | Capitalised to "Apartment" only |
| 03 | Empty similar_listings [] | Stays empty, not filled with demos |
| 04 | rag_insight mentions "RAG service timeout" | Error text preserved |
| 05 | routing_decision="residential" | Not changed to "High Priority" |
| 06 | 3 similar listing objects from RAG | Objects kept, not stringified |
| 07 | Chat text instead of JSON | Returns placeholders, confidence=0 |
| 08 | Markdown-wrapped input JSON | Outputs raw JSON only |
| 09 | Missing price_ils | Stays null, not invented |
| 10 | Agent added fake "Energy A+" certification | Certification not added |

---

## Version 1 — Marketing HTML brief

**Prompt:** `report_v1.txt`

**Results:** Valid JSON: **0/10** | No invented facts: **2/10** | **ALL passed: 0/10**

**Failure:** Returns HTML with invented headlines and buyer CTAs. Node 6b parser fails completely.

---

## Version 2 — HTML with no-invention rule

**Failure from v1:** Wrong output format (HTML not JSON).

**Change:** HTML brief + "do not invent facts."

**Prompt:** `report_v2.txt`

**Results:** Valid JSON: **0/10** | No invented facts: **7/10** | **ALL passed: 0/10**

**Failure:** Still HTML output. Downstream nodes expect JSON for routing (Node 8) and guardrails (Node 7).

---

## Version 3 — JSON with wrong schema

**Failure from v2:** Output format incompatible with pipeline.

**Change:** Request JSON with marketing-oriented keys (headline, cta_text).

**Prompt:** `report_v3.txt`

**Results:** Valid JSON: **8/10** | Schema matches Node 8 router: **0/10** | **ALL passed: 0/10**

**Failure:** Missing `routing_decision`, `image_scores`, `similar_listings` — Node 8 cannot route.

---

## Version 4 — Correct schema but demo substitution

**Failure from v3:** Wrong keys for downstream routing.

**Change:** Match Node 5 output schema; normalise types only.

**Prompt:** `report_v4.txt`

**Results:** Schema match: **10/10** | Preserves real data: **5/10** | **ALL passed: 5/10**

**Failure:** Model replaces Florentin listing with "Example Apartment in Tel Aviv" demo data (cases 01, 05). Fills empty `similar_listings` with fake entries (case 03).

---

## Version 5 — Production

**Failure from v4:** Demo substitution and fake enrichment.

**Change:** PRESERVE VERBATIM block, explicit FORBIDDEN list, placeholder fallback for unparseable input.

**Prompt:** `report_v5.txt` (deployed in n8n Node 6)

**Results:** **10/10**

**Deployed in:** `AI_Property_Triage_n8n.json` → Node 6 Final Report LLM Chain

---

## Summary — Layer 2 Final Pass Rates

| Surface | Node | v1 | v2 | v3 | v4 | v5 |
|---|---|---|---|---|---|---|
| Information Extractor | 4 | 0/10 | 0/10 | 3/10 | 4/10 | **10/10** |
| AI Agent | 5 | 0/10 | 0/10 | 3/10 | 4/10 | **10/10** |
| Final Report LLM Chain | 6 | 0/10 | 0/10 | 0/10 | 5/10 | **10/10** |

**Production prompt files:**
- `src/n8n/prompts/extractor_v5.txt`
- `src/n8n/prompts/agent_system_v5.txt`
- `src/n8n/prompts/report_v5.txt`
