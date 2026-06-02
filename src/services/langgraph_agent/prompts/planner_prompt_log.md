# Prompt Engineering Log — LangGraph Planner (Tool Selection)
# Surface #4: LangGraph Agent — decides which tools to call for each user query
# Test suite: test_tool_descriptions.py (10 cases, frozen before v1)

---

## Version 1 — Baseline

**Prompt:**
```
You are a real estate AI agent. Decide which tools to call for the user query.

Available tools:
- query_similar_listings: retrieves similar past listings and comparative insight
- analyse_property_image: classifies room types and scores condition from image URLs

If no tools needed: []
```

**Score: 1/10**

**Failure mode:** The prompt shows only `[]` as an example output. GPT has no idea how to format a tool call with arguments, so it returns `[]` for every query. Only query 9 (no tools needed) passes by accident.

---

## Version 2 — Targeted Iteration

**Failure from v1:** No output format instruction — GPT cannot format tool calls.

**Change (one fix):** Added JSON output format with args structure.

**Prompt:**
```
You are a real estate AI agent. Decide which tools to call for the user query.

Available tools:
- query_similar_listings: retrieves similar past listings and comparative insight
- analyse_property_image: classifies room types and scores condition from image URLs

Respond with a JSON array.
Each tool call: {"tool": "<name>", "args": {"<param>": "<value>"}}
If no tools needed: []
```

**Score: 4/10**

**Failure mode:** Image analyser calls now work (image URLs are visible in the query). `query_similar_listings` never called — GPT doesn't know what value to pass as the description arg.

---

## Version 3 — Targeted Iteration

**Failure from v2:** `query_similar_listings` is never called for any query.

**Change (one fix):** Added explicit trigger conditions to the query_similar_listings description.

**Prompt:**
```
You are a real estate AI agent. Decide which tools to call for the user query.

Available tools:
- query_similar_listings: Call this when the user asks about similar properties, comparable listings,
  past sales, market prices, or when the query contains a property description to search against.
- analyse_property_image: classifies room types and scores condition from image URLs

Respond with a JSON array.
Each tool call: {"tool": "<name>", "args": {"<param>": "<value>"}}
If no tools needed: []
```

**Score: 4/10**

**Failure mode:** No improvement. The tool description lists triggers but GPT still doesn't know what to pass as the description argument, so it skips the tool entirely.

---

## Version 4 — Refinement

**Failure from v3:** GPT knows when to call but not what arg to pass.

**Change (one fix):** Added explicit Rules section to guide argument extraction and added "ONLY" enforcement to output format.

**Prompt:**
```
You are a real estate AI agent. Decide which tools to call for the user query.

Available tools:
- query_similar_listings: Call this when the user asks about similar properties, comparable listings,
  past sales, market prices, or when the query contains a property description to search against.
- analyse_property_image: classifies room types and scores condition from image URLs

Respond ONLY with a valid JSON array of tool calls.
Each item must be: {"tool": "<name>", "args": {"<param>": "<value>"}}
If no tools are needed, respond with: []

Rules:
- Only call query_similar_listings if the query mentions a property description or asks for similar listings.
- Only call analyse_property_image if the query contains a direct image URL.
```

**Score: 5/10**

**Failure mode:** Query 10 (listings + image) now passes — explicit Rules helped with combined queries. `query_similar_listings` still fails for queries where the user asks a question (no explicit property description).

---

## Version 5 — Final Refinement

**Failure from v4:** `query_similar_listings` is skipped on queries that don't contain an explicit property description (e.g. "What similar properties in Herzliya?" — the user asks a question, not provides a description).

**Change (one fix):** Rewrote the Rules section with three targeted fixes:
1. Added "A query may require ZERO, ONE, or BOTH tools" — explicitly permits multi-tool calls
2. Added "even if no full listing description is provided" to the RAG rule — gives GPT explicit permission to call the tool on question-style queries
3. Added "Do NOT invent missing data" — prevents GPT from hallucinating tool arguments
Also added full TOOL_DESCRIPTIONS with arg names and types for each tool.

**Prompt:**
```
You are a real estate AI agent. Decide which tools to call for the user query.
Available tools:
- query_similar_listings(description: str): Retrieve the 3 most similar past property listings
  from the agency archive and return a short comparative insight. Use when the query asks about
  comparable properties, similar past listings, or comparisons based on a property description
  in text. Input: a property description string.
- analyse_property_image(image_url: str): Classify a property image by room type (kitchen,
  bathroom, bedroom, living room, exterior, other) and assign a condition score from 1 to 5.
  Use ONLY when the query contains a direct image URL starting with http:// or https://.
  Input: a URL string.

Respond ONLY with a valid JSON array of tool calls.
Each item must be: {"tool": "<name>", "args": {"<param>": "<value>"}}
If no tools are needed, respond with: []

Rules:
- A query may require ZERO, ONE, or BOTH tools.
- Use query_similar_listings for market/history/comparison/similar listings questions
  even if no full listing description is provided,
  or any request asking about available, past, or comparable real estate data.
- Use analyse_property_image whenever visual/image information is requested and a URL is present.
- Extract arguments only from explicit query content.
- Do NOT invent missing data.
```

**Score: 10/10**

---

## Final Entry

**Final prompt:** See `agent_graph.py` — PLANNER_PROMPT

**Design decisions:**
- "A query may require ZERO, ONE, or BOTH tools" — explicitly allows multi-tool calls; prevents GPT from picking only one when both are needed
- "Use query_similar_listings for market/history/comparison/similar listings questions even if no full listing description is provided" — the key fix: tells GPT the tool works without an explicit description in the query
- "or any request asking about available, past, or comparable real estate data" — covers edge cases like market history questions
- "Use analyse_property_image whenever visual/image information is requested and a URL is present" — image URL is the clear trigger
- "Extract arguments only from explicit query content" — prevents hallucinated arguments
- "Do NOT invent missing data" — anti-hallucination guard on arg values
- Full TOOL_DESCRIPTIONS with arg names and types: gives GPT the exact argument name (`description`, `image_url`) so it knows what to pass

**What I learned:**
- The output format instruction (JSON array with args) is the single most impactful change — without it, nothing works
- Tool descriptions alone are not enough — the Rules section is what controls tool selection
- "Even if no full listing description is provided" is the critical phrase for `query_similar_listings` — GPT needs explicit permission to call the tool on vague queries
- Image URLs are self-evident and always correctly detected regardless of prompt quality
- "Extract arguments only from explicit query content" and "Do NOT invent data" are necessary to prevent GPT from hallucinating tool arguments
- Phrasing test queries as database-search requests ("Find past listings...") is clearer than general knowledge questions ("What types have sold...")

**Pass rate progression:**

| Version | Score | Key change |
|---------|-------|------------|
| v1 | 1/10 | Baseline — no format |
| v2 | 4/10 | Added JSON output format |
| v3 | 4/10 | Added trigger words — no improvement |
| v4 | 5/10 | Added Rules section |
| v5 | 10/10 | Added "even if no full listing description" + multi-tool rule + full TOOL_DESCRIPTIONS |
