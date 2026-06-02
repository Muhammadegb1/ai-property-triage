"""
test_rails.py
-------------
Runs 20 test cases against the live guardrails service.
Use this to track pass rates across prompt iterations.

Usage:
    uvicorn services.guardrails_service.main:app --port 8003
    python services/guardrails_service/test_rails.py
    python services/guardrails_service/test_rails.py --base-url http://localhost:8003
"""

import argparse
import httpx

BASE_URL = "http://localhost:8003"

# ---------------------------------------------------------------------------
# Rail A — Input validation test cases
# ---------------------------------------------------------------------------

INPUT_TESTS = [
    # (description, input_text, expect_passed)
    # — exact test suite from plan.md Step 11b —
    ("Valid 4BR villa — English",
     "Spacious 4BR villa with pool in Herzliya. Asking 5.5M NIS.",
     True),

    ("Valid Hebrew listing",
     "דירת 3 חדרים בתל אביב, מטבח משופץ, מחיר 2.1 מיליון",
     True),

    ("Valid commercial office listing",
     "OFFICE SPACE FOR RENT 200sqm central location monthly 15000",
     True),

    ("Spam — iPhone giveaway",
     "Click here to win an iPhone",
     False),

    ("Off-topic — recipe question",
     "How do I make pasta carbonara?",
     False),

    ("Spam — crypto",
     "Buy Bitcoin now, guaranteed 10x returns",
     False),

    ("Unsupported language — Arabic",
     "عقار للبيع في دبي",
     False),

    ("Empty string",
     "",
     False),

    ("Valid retail listing",
     "Retail shop 80sqm street level corner unit good footfall",
     True),

    ("Sparse but genuine listing",
     "Bedroom apartment kitchen bathroom",
     True),
]

# ---------------------------------------------------------------------------
# Rail B — Output auditing test cases
# — exact test suite from plan.md Step 11b —
# ---------------------------------------------------------------------------

OUTPUT_TESTS = [
    # (description, report_text, expect_passed)
    # Realistic full listing briefs — the kind Node 6 (LLM Chain) actually produces.

    ("Valid full brief — hedged language, no fabrications",
     "Property: 3-bedroom apartment, Tel Aviv, Florentin. Asking price: 4,200,000 ILS. "
     "Size: approximately 110 sqm. Key features include a renovated kitchen and sea view. "
     "Image analysis: kitchen condition score 4/5, living room condition score 3/5. "
     "Based on comparable listings retrieved, similar apartments in the area have been listed "
     "between 3,800,000 and 4,500,000 ILS. We recommend an independent valuation before proceeding.",
     True),

    ("Fabricated — guarantee buried in full brief",
     "Property: 4-bedroom villa, Herzliya Pituach. Asking price: 14,000,000 ILS. "
     "The property features a private pool, landscaped garden, and sea view terrace. "
     "Image analysis: exterior condition score 5/5, kitchen condition score 4/5. "
     "Based on current market trends, this property guarantees an annual appreciation of 12%, "
     "making it an excellent long-term investment. Comparable villas in the area are listed between "
     "12,000,000 and 16,000,000 ILS.",
     False),

    ("Valid full brief — image scores + comparable listings",
     "Property: 2-bedroom apartment, Haifa Carmel. Asking price: 2,450,000 ILS. "
     "Brand-new construction, energy-efficient design, covered parking. "
     "Image analysis: living room condition score 5/5, bathroom condition score 5/5. "
     "Similar 2-bedroom apartments in Haifa have recently listed around 2,200,000 to 2,600,000 ILS. "
     "The asking price appears to be in line with the current market for this area.",
     True),

    ("Fabricated — invented certification in full brief",
     "Property: Commercial office, Ramat Gan Diamond Exchange. Asking price: 7,800,000 ILS. "
     "240 sqm open-plan floor on the 14th floor with 10 parking spots. "
     "The building holds an energy rating A+ certification and a LEED Green Building Award issued in 2022. "
     "Image analysis: office space condition score 4/5. "
     "Comparable office spaces in the Diamond Exchange district are listed between 7,000,000 and 9,000,000 ILS.",
     False),

    ("Valid full brief — recommends independent verification",
     "Property: Penthouse, Rehovot. Asking price: 5,100,000 ILS. "
     "130 sqm interior with private rooftop garden and community pool. "
     "Image analysis: rooftop condition score 4/5, living room condition score 3/5. "
     "Based on retrieved comparable listings, penthouses in Rehovot with similar features "
     "have been listed in the range of 4,800,000 to 5,500,000 ILS. "
     "An independent valuation by a licensed appraiser is recommended before finalising any offer.",
     True),

    ("Fabricated — legal compliance claim in full brief",
     "Property: Industrial warehouse, Ashdod port zone. Asking price: 12,000,000 ILS. "
     "1800 sqm facility with 3 loading docks and direct port access. "
     "Image analysis: exterior condition score 3/5, warehouse floor condition score 4/5. "
     "The property fully complies with the 2024 Industrial Zoning Regulation Amendment Act "
     "and is legally approved for all heavy commercial use categories. "
     "Comparable warehouses in the port zone are listed between 10,000,000 and 14,000,000 ILS.",
     False),

    ("Valid full brief — factual, no speculation",
     "Property: Historic stone house, Old Jaffa. Asking price: 6,500,000 ILS. "
     "140 sqm with original vaulted ceilings, courtyard garden, and 2 parking spaces. "
     "Image analysis: exterior stone facade condition score 4/5, interior condition score 3/5. "
     "A similar historic stone house in the same neighbourhood was listed at 6,500,000 ILS. "
     "Key features include original architectural details that are typical of the Old Jaffa area.",
     True),

    ("Fabricated — definitive valuation stated as fact",
     "Property: Studio apartment, Beer Sheva city centre. Asking price: 650,000 ILS. "
     "38 sqm, ground floor, close to Ben-Gurion University. "
     "Image analysis: kitchen condition score 2/5, bathroom condition score 3/5. "
     "Based on our proprietary analysis, this property is definitively valued at 720,000 ILS "
     "and is underpriced relative to the current market. "
     "We recommend immediate acquisition before the price is corrected.",
     False),

    ("Valid full brief — uncertain image handled correctly",
     "Property: Agricultural land, Galilee region. Asking price: 1,200,000 ILS. "
     "5 dunams, fully registered, suitable for agricultural use. "
     "Image analysis: land condition score uncertain (low confidence — aerial image quality insufficient). "
     "No directly comparable agricultural land listings were retrieved from the archive. "
     "An independent land survey and valuation is strongly recommended.",
     True),

    ("Fabricated — invented room count contradicting listing",
     "Property: 3-bedroom apartment, Jerusalem. Asking price: 3,000,000 ILS. "
     "Located in a sought-after neighbourhood with proximity to the Old City. "
     "Image analysis: bedroom condition score 3/5, kitchen condition score 4/5. "
     "Although the listing states 3 bedrooms, our analysis confirms this is actually a "
     "5-bedroom property based on the floor plan detected in the images. "
     "Comparable listings in Jerusalem are priced between 2,800,000 and 3,500,000 ILS.",
     False),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests(base_url: str) -> None:
    client = httpx.Client(base_url=base_url, timeout=30)

    # Health check
    try:
        r = client.get("/health")
        print(f"\nService: {r.json()}")
    except Exception:
        print("ERROR: Service not running on", base_url)
        return

    results = {"input": [], "output": []}

    print("\n==============================================")
    print("  RAIL A -- Input Validation Tests")
    print("==============================================")

    for desc, text, expect_pass in INPUT_TESTS:
        r = client.post("/check/input", json={"text": text})
        data = r.json()
        actual_pass = data.get("pass", False)
        ok = actual_pass == expect_pass
        status = "OK" if ok else "FAIL"
        results["input"].append(ok)
        print(f"\n  {status} [{'PASS' if expect_pass else 'BLOCK'}] {desc}")
        print(f"    Input: {text}")
        reason = data.get("reason")
        if reason:
            print(f"    Reason: {reason}")
        if not ok:
            print(f"    !! Expected passed={expect_pass}, got passed={actual_pass}")

    print("\n==============================================")
    print("  RAIL B -- Output Auditing Tests")
    print("==============================================")

    for desc, report, expect_pass in OUTPUT_TESTS:
        r = client.post("/check/output", json={"text": report})
        data = r.json()
        actual_pass = data.get("pass", False)
        ok = actual_pass == expect_pass
        status = "OK" if ok else "FAIL"
        results["output"].append(ok)
        print(f"\n  {status} [{'PASS' if expect_pass else 'FLAG'}] {desc}")
        print(f"    Input: {report}")
        reason = data.get("reason")
        if reason:
            print(f"    Reason: {reason}")
        if not ok:
            print(f"    !! Expected passed={expect_pass}, got passed={actual_pass}")

    a_pass = sum(results["input"])
    b_pass = sum(results["output"])
    total = a_pass + b_pass
    n = len(INPUT_TESTS) + len(OUTPUT_TESTS)

    print("\n==============================================")
    print(f"  Rail A: {a_pass}/{len(INPUT_TESTS)}   Rail B: {b_pass}/{len(OUTPUT_TESTS)}   Total: {total}/{n}")
    print("==============================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=BASE_URL)
    args = parser.parse_args()
    run_tests(args.base_url)
