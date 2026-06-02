"""
test_tool_descriptions.py
--------------------------
Tests tool selection accuracy across prompt versions.
Runs all 10 benchmark queries and checks if the agent selected the correct tools.

Usage:
    uvicorn services.langgraph_agent.main:app --port 8004
    python services/langgraph_agent/test_tool_descriptions.py
"""

import argparse
import httpx

BASE_URL = "http://localhost:8004"

BENCHMARK = [
    # (description, query, expected_tools)
    (
        "Similar listings in Herzliya",
        "What similar properties have been listed in Herzliya?",
        ["query_similar_listings"],
    ),
    (
        "Analyse kitchen image",
        "Analyse this image: https://example.com/kitchen.jpg",
        ["analyse_property_image"],
    ),
    (
        "Comparable listings + bathroom image",
        "Find comparable listings AND assess this image: https://example.com/bathroom.jpg",
        ["query_similar_listings", "analyse_property_image"],
    ),
    (
        "Renovation advice - description only",
        "What renovation work is needed? Description: worn kitchen tiles, cracked bathroom grout.",
        ["query_similar_listings"],
    ),
    (
        "Rooms needing attention - image only",
        "Which rooms need attention? https://example.com/livingroom.jpg",
        ["analyse_property_image"],
    ),
    (
        "3BR near sea with parking",
        "Are there similar 3-bedroom apartments near the sea with parking?",
        ["query_similar_listings"],
    ),
    (
        "Exterior condition - image only",
        "What is the condition of the exterior? https://example.com/exterior.jpg",
        ["analyse_property_image"],
    ),
    (
        "Search listings above 3M",
        "Find past listings of apartments or villas priced above 3 million ILS.",
        ["query_similar_listings"],
    ),
    (
        "General knowledge - no tools",
        "What is a cap rate in real estate?",
        [],
    ),
    (
        "Price range - listings + bedroom image",
        "Based on similar listings and this bedroom image, what price range is right? https://example.com/bedroom.jpg",
        ["query_similar_listings", "analyse_property_image"],
    ),
]


def tools_match(actual: list[str], expected: list[str]) -> bool:
    return sorted(actual) == sorted(expected)


def run_tests(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=60)

    try:
        r = client.get("/health")
        print(f"\nService: {r.json()}")
    except Exception:
        print("ERROR: Agent not running on", base_url)
        return

    passed = 0
    print("\n" + "=" * 54)
    print("  Tool Description Benchmark - 10 queries")
    print("=" * 54)

    for desc, query, expected in BENCHMARK:
        r = client.post("/agent/run", json={"query": query})
        data = r.json()
        actual = data.get("tools_used", [])
        ok = tools_match(actual, expected)
        status = "OK" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  [{status}] {desc}")
        if not ok:
            print(f"      Expected: {expected}")
            print(f"      Got:      {actual}")

    print(f"\n{'=' * 54}")
    print(f"  Score: {passed}/{len(BENCHMARK)}")
    print(f"{'=' * 54}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    run_tests(args.base_url)
