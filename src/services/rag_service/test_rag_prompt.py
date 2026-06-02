"""
test_rag_prompt.py
------------------
Tests the RAG service insight quality across prompt versions.

Checks per query:
  1. Citation         — insight contains at least one [LST-XXX] reference
  2. Multi-citation   — at least 2 of the 3 retrieved listings are cited
  3. Length           — insight is 2-5 sentences (not a single-sentence echo)
  4. Hallucination    — large numbers (3+ digits) and amenity keywords in the
                        insight must appear in the query or retrieved listings;
                        numbers attributed to the new listing must appear in the query

Usage:
    uvicorn services.rag_service.main:app --port 8001
    python services/rag_service/test_rag_prompt.py
"""

import argparse
import re
import httpx

BASE_URL = "http://localhost:8001"

# ---------------------------------------------------------------------------
# 10 fixed test cases — FROZEN before v1 runs. Do not change between versions.
# ---------------------------------------------------------------------------
TEST_CASES = [
    "3-bedroom apartment in Tel Aviv, renovated kitchen, sea view, asking 4200000 ILS.",
    "Studio apartment in city center, affordable, 38sqm, 650000 ILS.",
    "5-bedroom villa with private pool and landscaped garden in Herzliya, 18500000 ILS.",
    "Commercial office space 200sqm in Ramat Gan, 10 parking spots, 7800000 ILS.",
    "2-bedroom apartment near the beach with parking, Haifa, 2400000 ILS.",
    "Retail shop 80sqm with street frontage, high foot traffic, Jerusalem.",
    "Penthouse 130sqm with rooftop garden, community pool, Rehovot, 5100000 ILS.",
    "Agricultural land 5 dunams in the Galilee region, fully registered, 1200000 ILS.",
    "Historic stone house in Old Jaffa, 140sqm, vaulted ceilings, courtyard, 6500000 ILS.",
    "Industrial warehouse 1800sqm in Ashdod port zone, 3 loading docks, 12000000 ILS.",
]

CITATION_PATTERN = re.compile(r'\[LST-\d+\]')
# Only match 3+ digit numbers — avoids false positives from
# fragments like "9" in "9.8M" or "4" in "4.2M".
NUMBER_PATTERN = re.compile(r'\b\d{3,}[\d,]*(?:\.\d+)?\b')

# Specific amenities and certifications that are easy to fabricate
CHECKABLE_KEYWORDS = [
    "pool", "parking", "garden", "balcony", "elevator", "garage",
    "storage", "gym", "terrace", "rooftop", "fireplace",
    "certified", "leed", "class a", "guarantee", "guaranteed",
    "legally", "approved", "permit",
]


def extract_numbers(text: str) -> set:
    # Remove citation patterns first so [LST-007] doesn't produce '007'
    clean = CITATION_PATTERN.sub("", text)
    # Strip units attached to numbers (80sqm → 80, 200sqm → 200)
    clean = re.sub(r'(\d+)sqm', r'\1 ', clean, flags=re.IGNORECASE)
    return set(NUMBER_PATTERN.findall(clean.replace(",", "")))


def count_citations(insight: str) -> int:
    """Count unique [LST-XXX] citations in the insight."""
    matches = CITATION_PATTERN.findall(insight)
    return len(set(matches))


def check_invented_keywords(insight: str, query: str, similar_listings: list) -> list:
    source_text = (query + " " + " ".join(
        l.get("description", "") + " " + l.get("title", "")
        for l in similar_listings
    )).lower()
    insight_lower = insight.lower()
    invented = []
    for keyword in CHECKABLE_KEYWORDS:
        if keyword in insight_lower and keyword not in source_text:
            invented.append(keyword)
    return invented


def check_misattributed_numbers(insight: str, query: str) -> list:
    """
    Detects numbers attributed to the new listing that don't appear in the query.
    For each sentence mentioning 'new listing', checks the text before the first
    citation — numbers there are likely claimed as attributes of the new listing.
    """
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', insight.strip()) if s.strip()]
    query_numbers = extract_numbers(query)
    misattributed = []
    for sentence in sentences:
        if not re.search(r'\bnew listing\b', sentence, re.IGNORECASE):
            continue
        pre_citation = CITATION_PATTERN.split(sentence)[0]
        bad = extract_numbers(pre_citation) - query_numbers
        misattributed.extend(list(bad))
    return [f"{n}(misattributed)" for n in set(misattributed)]


def check_hallucination(insight: str, query: str, similar_listings: list) -> tuple[bool, list]:
    source_text = query + " " + " ".join(
        l.get("description", "") + " " + l.get("title", "")
        for l in similar_listings
    )
    # Check invented numbers (3+ digits only)
    insight_numbers = extract_numbers(insight)
    source_numbers = extract_numbers(source_text)
    invented_numbers = insight_numbers - source_numbers

    # Check invented keywords
    invented_keywords = check_invented_keywords(insight, query, similar_listings)

    # Check numbers misattributed to the new listing
    misattributed = check_misattributed_numbers(insight, query)

    all_invented = list(invented_numbers) + invented_keywords + misattributed
    return len(all_invented) == 0, all_invented


def check_insight(insight: str, query: str, similar_listings: list) -> dict:
    has_citation = bool(CITATION_PATTERN.search(insight))
    citation_count = count_citations(insight)
    multi_citation = citation_count >= 2
    is_non_empty = len(insight.strip()) > 10
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', insight.strip()) if s.strip()]
    sentence_count = len(sentences)
    within_length = 2 <= sentence_count <= 5
    no_hallucination, invented = check_hallucination(insight, query, similar_listings)
    return {
        "has_citation": has_citation,
        "citation_count": citation_count,
        "multi_citation": multi_citation,
        "is_non_empty": is_non_empty,
        "sentence_count": sentence_count,
        "within_length": within_length,
        "no_hallucination": no_hallucination,
        "invented": invented,
    }


def run_tests(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=120)

    try:
        r = client.get("/health")
        data = r.json()
        print(f"\nService: {data}  |  Vector store: {data.get('vector_store', 'unknown')}")
    except Exception:
        print("ERROR: RAG service not running on", base_url)
        return

    citation_ok = 0
    multi_citation_ok = 0
    length_ok = 0
    no_halluc_ok = 0
    all_pass = 0
    total = len(TEST_CASES)

    print(f"\n{'='*60}")
    print("  RAG Prompt Benchmark - 10 queries")
    print(f"{'='*60}")

    for i, description in enumerate(TEST_CASES, start=1):
        r = client.post("/query", json={"description": description})
        data = r.json()
        insight = data.get("insight", "")
        similar_listings = data.get("similar_listings", [])
        checks = check_insight(insight, description, similar_listings)

        c_mark = "OK" if checks["has_citation"] else "FAIL"
        m_mark = "OK" if checks["multi_citation"] else "FAIL"
        l_mark = "OK" if checks["within_length"] else "FAIL"
        h_mark = "OK" if checks["no_hallucination"] else "FAIL"
        passed = (
            checks["has_citation"]
            and checks["multi_citation"]
            and checks["within_length"]
            and checks["no_hallucination"]
        )

        if checks["has_citation"]:
            citation_ok += 1
        if checks["multi_citation"]:
            multi_citation_ok += 1
        if checks["within_length"]:
            length_ok += 1
        if checks["no_hallucination"]:
            no_halluc_ok += 1
        if passed:
            all_pass += 1

        status = "PASS" if passed else "FAIL"
        invented_str = f" (invented: {checks['invented']})" if checks["invented"] else ""
        print(f"\n  [{status}] Case {i:02d}: {description}.")
        print(
            f"    Citation [{c_mark}] ({checks['citation_count']} of 3) [{m_mark}] | "
            f"Length {checks['sentence_count']}s [{l_mark}] | "
            f"Hallucination [{h_mark}]{invented_str}"
        )
        print(f"    Insight: {insight}")
        if similar_listings:
            print(f"    Retrieved listings ({len(similar_listings)}):")
            for lst in similar_listings:
                lst_id = lst.get("id", lst.get("listing_id", "?"))
                lst_title = lst.get("title", lst.get("description", "")[:60])
                print(f"      - [{lst_id}] {lst_title}")

    print(f"\n{'='*60}")
    print(f"  Citation present       : {citation_ok}/{total}")
    print(f"  Multi-citation (>=2)   : {multi_citation_ok}/{total}")
    print(f"  Length OK (2-5 s)      : {length_ok}/{total}")
    print(f"  No hallucination       : {no_halluc_ok}/{total}")
    print(f"  ALL checks passed      : {all_pass}/{total}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    run_tests(args.base_url)