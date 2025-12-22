"""
MIRA Phase 3 - SMB Owner Conversation Test

This script demonstrates a complete conversation flow as a small business owner,
testing all implemented features:
- Greeting and initial state
- SMB mode detection
- Brand/brief extraction
- Program generation
- Activation mapping
- Optimization suggestions
- Session persistence
"""

import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8080"
CHAT_ENDPOINT = f"{BASE_URL}/v1/rjm/chat"

# Store conversation for output
conversation_log = []
session_id = None


def log_message(role: str, content: str, state: str = None, extras: dict = None):
    """Log a message to the conversation."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "content": content,
    }
    if state:
        entry["state"] = state
    if extras:
        entry.update(extras)
    conversation_log.append(entry)

    # Print to console
    print(f"\n{'='*60}")
    if role == "user":
        print(f"USER: {content}")
    else:
        print(f"MIRA: {content}")
        if state:
            print(f"[State: {state}]")
    print(f"{'='*60}")


def send_message(user_message: str, state: str = None, brand_name: str = None, brief: str = None):
    """Send a message to MIRA and get response."""
    global session_id

    payload = {
        "messages": [{"role": "user", "content": user_message}],
    }

    if session_id:
        payload["session_id"] = session_id
    if state:
        payload["state"] = state
    if brand_name:
        payload["brand_name"] = brand_name
    if brief:
        payload["brief"] = brief

    log_message("user", user_message)

    try:
        response = requests.post(CHAT_ENDPOINT, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()

        session_id = data.get("session_id")
        reply = data.get("reply", "")
        next_state = data.get("state", "")
        debug_state = data.get("debug_state_was", "")

        log_message("mira", reply, next_state, {
            "session_id": session_id,
            "debug_state_was": debug_state
        })

        return data
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        log_message("system", error_msg)
        return None


def run_smb_conversation():
    """Run a complete SMB owner conversation demonstrating all features."""
    global session_id

    print("\n" + "="*80)
    print("MIRA PHASE 3 - SMB OWNER CONVERSATION TEST")
    print("Testing: Greeting, Mode Detection, Program Generation, Activation, Optimization")
    print("="*80)

    # Turn 1: Initial greeting
    print("\n[TEST 1: Initial Greeting - Testing STATE_GREETING]")
    response = send_message("Hey there!")
    current_state = response.get("state") if response else None

    # Turn 2: Introduce as small business owner (SMB mode detection)
    print("\n[TEST 2: SMB Mode Detection - Small Business Language]")
    response = send_message(
        "I run a small business - a local bakery called Sweet Sunrise. We're known for our artisan breads and pastries.",
        state=current_state
    )
    current_state = response.get("state") if response else None

    # Turn 3: Provide brief
    print("\n[TEST 3: Brief Extraction - Campaign Details]")
    response = send_message(
        "I want to launch a campaign for our new weekend brunch menu. We're targeting families in the neighborhood who want a cozy breakfast spot. Our budget is around $15,000.",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 4: Confirm audience
    print("\n[TEST 4: Audience Confirmation]")
    response = send_message(
        "Yes, families with kids, especially moms who appreciate quality baked goods and a warm atmosphere.",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 5: Request activation
    print("\n[TEST 5: Activation Mapping - Testing Reasoning Engine Integration]")
    response = send_message(
        "This looks great! Can you map out the activation plan for me?",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 6: Ask optimization question (scale)
    print("\n[TEST 6: Optimization - Scale Request]")
    response = send_message(
        "What if we need more scale? I want to reach more people in the area.",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 7: Ask about quality
    print("\n[TEST 7: Optimization - Quality Request]")
    response = send_message(
        "Actually, I'm more concerned about reaching the right people, not just anyone. How can we focus on quality?",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 8: Ask definitional question
    print("\n[TEST 8: Definitional Q&A - What are RJM Personas?]")
    response = send_message(
        "By the way, what exactly are RJM Personas? I want to understand what I'm getting.",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )
    current_state = response.get("state") if response else None

    # Turn 9: Accept the plan
    print("\n[TEST 9: Acceptance - Testing Exit State]")
    response = send_message(
        "This all sounds great! I think we're good to go.",
        state=current_state,
        brand_name="Sweet Sunrise Bakery",
        brief="Local bakery launching weekend brunch menu targeting neighborhood families"
    )

    print("\n" + "="*80)
    print("CONVERSATION COMPLETE")
    print("="*80)


def save_conversation():
    """Save the conversation to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests/smb_conversation_{timestamp}.txt"

    with open(filename, "w", encoding="utf-8") as f:
        f.write("MIRA PHASE 3 - SMB OWNER CONVERSATION LOG\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Session ID: {session_id}\n")
        f.write("=" * 80 + "\n\n")

        for entry in conversation_log:
            f.write(f"[{entry['timestamp']}]\n")
            role = entry['role'].upper()
            f.write(f"{role}:\n")
            f.write(f"{entry['content']}\n")
            if 'state' in entry:
                f.write(f"(State: {entry['state']})\n")
            if 'session_id' in entry:
                f.write(f"(Session: {entry['session_id']})\n")
            f.write("\n" + "-" * 40 + "\n\n")

    print(f"\nConversation saved to: {filename}")
    return filename


def save_json_log():
    """Save conversation as JSON for detailed analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tests/smb_conversation_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump({
            "test_name": "SMB Owner Conversation Test",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "conversation": conversation_log
        }, f, indent=2)

    print(f"JSON log saved to: {filename}")
    return filename


if __name__ == "__main__":
    try:
        run_smb_conversation()
        txt_file = save_conversation()
        json_file = save_json_log()

        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Total turns: {len([e for e in conversation_log if e['role'] == 'user'])}")
        print(f"Session ID: {session_id}")
        print(f"Conversation file: {txt_file}")
        print(f"JSON log file: {json_file}")
        print("\nFeatures tested:")
        print("  - Initial greeting (STATE_GREETING)")
        print("  - SMB mode detection (small business language)")
        print("  - Brand/brief extraction")
        print("  - Program generation")
        print("  - Activation mapping (Reasoning Engine)")
        print("  - Optimization suggestions (scale, quality)")
        print("  - Definitional Q&A")
        print("  - Session persistence")
        print("  - Exit state handling")
        print("="*80)

    except Exception as e:
        print(f"\nError running test: {e}")
        import traceback
        traceback.print_exc()
