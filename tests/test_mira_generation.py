#!/usr/bin/env python3
"""
Test script for MIRA persona program generation.
Runs all 5 test cases and saves outputs to a formatted text file.

Usage:
    1. Make sure the FastAPI server is running:
       uvicorn app.main:app --reload
    
    2. Run this script:
       python tests/test_mira_generation.py
       # or
       ./tests/test_mira_generation.py
    
    3. Check the output file:
       tests/mira_test_results.txt

The script will:
    - Test all 5 predefined brand/brief combinations
    - Save formatted JSON outputs to mira_test_results.txt
    - Include both program_json and program_text for each test case
"""

import json
import httpx
from datetime import datetime
from pathlib import Path

# Test inputs
TEST_CASES = [
    {
        "brand_name": "BrunchBox",
        "brief": "Family-focused QSR chain wants to relaunch its weekend brunch menu with neighborhood storytelling and comfort rituals."
    },
    {
        "brand_name": "Everyday Threads",
        "brief": "National retail brand wants to launch a spring refresh campaign focused on everyday style, weekend errands, and family shopping trips."
    },
    {
        "brand_name": "Northstar Motors",
        "brief": "Auto brand is promoting a new family SUV for road trips, long weekends, and music-driven adventures with friends."
    },
    {
        "brand_name": "Heartland Bank",
        "brief": "Regional bank wants to spotlight community pride, long-term stability, and everyday financial confidence for local families."
    },
    {
        "brand_name": "L'Oréal",
        "brief": "Beauty brand focused on ritual, self-expression, and everyday confidence."
    }
]

# API endpoint
API_BASE_URL = "http://localhost:8000"
GENERATE_ENDPOINT = f"{API_BASE_URL}/v1/rjm/generate"


def format_json_output(obj, indent=2):
    """Format JSON object with proper indentation."""
    return json.dumps(obj, indent=indent, ensure_ascii=False)


def run_test_case(test_num, input_data):
    """Run a single test case and return the response."""
    print(f"Running test case {test_num}...")
    try:
        with httpx.Client(timeout=120.0) as client:  # 2 minute timeout for generation
            response = client.post(
                GENERATE_ENDPOINT,
                json=input_data
            )
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        print(f"Error in test case {test_num}: {e}")
        return None


def write_test_results(output_file_path):
    """Run all test cases and write results to file."""
    results = []
    
    # Run all test cases
    for idx, test_input in enumerate(TEST_CASES, start=1):
        print(f"\n{'='*60}")
        print(f"Test Case {idx}: {test_input['brand_name']}")
        print(f"{'='*60}")
        
        result = run_test_case(idx, test_input)
        if result:
            results.append({
                "test_num": idx,
                "input": test_input,
                "output": result
            })
            print(f"✓ Test case {idx} completed successfully")
        else:
            print(f"✗ Test case {idx} failed")
    
    # Write results to file
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write("MIRA PERSONA PROGRAM GENERATION TEST RESULTS\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        
        for result in results:
            test_num = result["test_num"]
            input_data = result["input"]
            output_data = result["output"]
            
            f.write(f"\n{'='*80}\n")
            f.write(f"INPUT {test_num}:\n")
            f.write(f"{'='*80}\n\n")
            f.write(format_json_output(input_data))
            f.write("\n\n")
            
            f.write(f"\n{'='*80}\n")
            f.write(f"OUTPUT {test_num}:\n")
            f.write(f"{'='*80}\n\n")
            f.write(format_json_output(output_data))
            f.write("\n\n")
            
            # Also write the program_text separately for readability
            if "program_text" in output_data:
                f.write(f"\n{'='*80}\n")
                f.write(f"PROGRAM TEXT {test_num}:\n")
                f.write(f"{'='*80}\n\n")
                f.write(output_data["program_text"])
                f.write("\n\n")
    
    print(f"\n{'='*60}")
    print(f"Test results saved to: {output_file_path}")
    print(f"Total test cases: {len(results)}/{len(TEST_CASES)}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Determine output file path
    script_dir = Path(__file__).parent
    output_file = script_dir / "mira_test_results.txt"
    
    print("MIRA Persona Program Generation Test Script")
    print("=" * 60)
    print(f"API Endpoint: {GENERATE_ENDPOINT}")
    print(f"Output file: {output_file}")
    print("=" * 60)
    
    # Check if server is running
    try:
        with httpx.Client(timeout=5.0) as client:
            health_response = client.get(f"{API_BASE_URL}/status")
            if health_response.status_code == 200:
                print("✓ Server is running")
            else:
                print("⚠ Server responded with non-200 status")
    except httpx.RequestError:
        print("✗ ERROR: Cannot connect to server!")
        print(f"   Make sure the server is running at {API_BASE_URL}")
        print("   Start it with: uvicorn app.main:app --reload")
        exit(1)
    
    # Run tests
    write_test_results(output_file)

