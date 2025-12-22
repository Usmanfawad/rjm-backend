#!/usr/bin/env python3
"""
Interactive CLI tester for the MIRA chat endpoint.

This script:
- Prompts you for brand name and brief once.
- Then runs an interactive chat loop, sending each user message to /v1/rjm/chat.
- Tracks behavioral state across turns.
- Saves the full conversation to a timestamped .txt file in tests/.

Usage:
  1. Start the FastAPI server:
       uvicorn app.main:app --reload

  2. Run this script:
       python tests/mira_chat_cli.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import httpx


API_BASE_URL = "http://localhost:8080"
CHAT_ENDPOINT = f"{API_BASE_URL}/v1/rjm/chat"


def pretty(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False)


def main() -> None:
    print("MIRA Chat CLI Tester")
    print("=" * 60)
    print(f"Endpoint: {CHAT_ENDPOINT}")
    print("Type 'exit' to end the conversation.\n")

    brand_name = input("Brand name (optional, you can leave blank for now): ").strip()
    brief = input("Brief / campaign description (optional, you can leave blank for now): ").strip()
    print("")

    messages: List[Dict[str, str]] = []
    state: str | None = None
    session_id: str | None = None

    transcript_lines: List[str] = []
    transcript_lines.append("MIRA CHAT CLI RUN")
    transcript_lines.append("=" * 80)
    transcript_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    transcript_lines.append(f"Endpoint: {CHAT_ENDPOINT}")
    transcript_lines.append("=" * 80)
    transcript_lines.append("")

    try:
        with httpx.Client(timeout=120.0) as client:
            while True:
                user_text = input("You: ").strip()
                if not user_text:
                    continue
                if user_text.lower() in {"exit", "quit"}:
                    print("Ending conversation.")
                    break

                messages.append({"role": "user", "content": user_text})

                payload: Dict[str, Any] = {
                    "messages": messages,
                }
                if state:
                    payload["state"] = state
                if session_id:
                    payload["session_id"] = session_id
                if brand_name:
                    payload["brand_name"] = brand_name
                if brief:
                    payload["brief"] = brief

                try:
                    resp = client.post(CHAT_ENDPOINT, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.RequestError as exc:
                    print(f"[ERROR] Request failed: {exc}")
                    break
                except httpx.HTTPStatusError as exc:
                    print(f"[ERROR] Server returned {exc.response.status_code}: {exc.response.text}")
                    break

                reply = data.get("reply", "")
                state = data.get("state") or state
                session_id = data.get("session_id") or session_id

                print("\nMIRA:")
                print(reply)
                print("")

                # Append assistant message to history for next turn
                messages.append({"role": "assistant", "content": reply})

                # Log to transcript
                transcript_lines.append("You:")
                transcript_lines.append(user_text)
                transcript_lines.append("")
                transcript_lines.append("MIRA:")
                transcript_lines.append(reply)
                transcript_lines.append(f"(Next state: {state}, session: {session_id})")
                transcript_lines.append("-" * 80)

    finally:
        # Save transcript
        tests_dir = Path(__file__).parent
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = tests_dir / f"mira_chat_run_{timestamp}.txt"
        with output_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(transcript_lines))

        print(f"\nConversation saved to: {output_path}")


if __name__ == "__main__":
    main()


