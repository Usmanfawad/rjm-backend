"""
Test script for LLM-based category detection.

This validates that well-known brands are correctly categorized:
- Starbucks -> Culinary & Dining (NOT CPG)
- Fendi -> Luxury & Fashion (NOT CPG)
- Verizon -> Tech & Wireless (NOT CPG)
- Hillstone -> Culinary & Dining (NOT CPG)
- Peloton -> Sports & Fitness (NOT CPG)

Run with: python -m pytest tests/test_category_detection.py -v
Or directly: python tests/test_category_detection.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Test cases: (brand_name, brief, expected_category)
TEST_CASES = [
    ("Starbucks", "Coffee brand looking to drive foot traffic and loyalty", "Culinary & Dining"),
    ("Fendi", "Luxury fashion brand launching new handbag collection", "Luxury & Fashion"),
    ("Verizon", "Wireless carrier promoting 5G network coverage", "Tech & Wireless"),
    ("Hillstone", "Upscale casual dining restaurant group", "Culinary & Dining"),
    ("Peloton", "Connected fitness brand promoting at-home workout equipment", "Sports & Fitness"),
    ("Nike", "Athletic apparel and footwear brand", "Sports & Fitness"),
    ("BMW", "Luxury automotive brand launching new SUV", "Auto"),
    ("Chase", "Banking and credit card services", "Finance & Insurance"),
    ("Marriott", "Hotel chain promoting loyalty program", "Travel & Hospitality"),
    ("Netflix", "Streaming entertainment service", "Entertainment"),
    ("Tide", "Laundry detergent brand", "CPG"),
    ("Coca-Cola", "Beverage brand running summer campaign", "CPG"),
]


def test_category_detection():
    """Test LLM-based category detection for known brands."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    print("\n" + "=" * 70)
    print("CATEGORY DETECTION TEST RESULTS")
    print("=" * 70 + "\n")
    
    passed = 0
    failed = 0
    
    for brand_name, brief, expected in TEST_CASES:
        detected = infer_category_with_llm(brand_name, brief)
        status = "✓ PASS" if detected == expected else "✗ FAIL"
        
        if detected == expected:
            passed += 1
            print(f"{status}: {brand_name}")
            print(f"       Expected: {expected}")
            print(f"       Detected: {detected}\n")
        else:
            failed += 1
            print(f"{status}: {brand_name}")
            print(f"       Expected: {expected}")
            print(f"       Detected: {detected} <-- WRONG\n")
    
    print("=" * 70)
    print(f"SUMMARY: {passed} passed, {failed} failed out of {len(TEST_CASES)} tests")
    print("=" * 70)
    
    return failed == 0


def test_starbucks_not_cpg():
    """Starbucks should be Culinary & Dining, not CPG."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    category = infer_category_with_llm("Starbucks", "Coffee brand campaign")
    assert category == "Culinary & Dining", f"Starbucks detected as {category}, expected Culinary & Dining"


def test_fendi_not_cpg():
    """Fendi should be Luxury & Fashion, not CPG."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    category = infer_category_with_llm("Fendi", "Luxury fashion brand")
    assert category == "Luxury & Fashion", f"Fendi detected as {category}, expected Luxury & Fashion"


def test_verizon_not_cpg():
    """Verizon should be Tech & Wireless, not CPG."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    category = infer_category_with_llm("Verizon", "Wireless carrier 5G campaign")
    assert category == "Tech & Wireless", f"Verizon detected as {category}, expected Tech & Wireless"


def test_peloton_not_cpg():
    """Peloton should be Sports & Fitness, not CPG."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    category = infer_category_with_llm("Peloton", "Connected fitness brand")
    assert category == "Sports & Fitness", f"Peloton detected as {category}, expected Sports & Fitness"


def test_hillstone_not_cpg():
    """Hillstone should be Culinary & Dining, not CPG."""
    from app.services.rjm_ingredient_canon import infer_category_with_llm
    
    category = infer_category_with_llm("Hillstone", "Upscale restaurant group")
    assert category == "Culinary & Dining", f"Hillstone detected as {category}, expected Culinary & Dining"


if __name__ == "__main__":
    # Run directly for quick validation
    success = test_category_detection()
    sys.exit(0 if success else 1)

