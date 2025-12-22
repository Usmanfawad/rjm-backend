"""
Tests for MIRA chat functionality.

Covers:
- Chat state transitions
- Mode detection
- Session management
- Reasoning Engine integration
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.mira_chat import (
    _detect_mode,
    _apply_mode_styling,
    _get_last_user_message,
    _classify_input_label,
    GREETING_STATE,
    INPUT_STATE,
    CLARIFICATION_STATE,
    PROGRAM_GENERATION_STATE,
    REASONING_BRIDGE_STATE,
    ACTIVATION_STATE,
    EXIT_STATE,
    OPTIMIZATION_STATE,
)
from app.services.mira_session import (
    SessionState,
    get_session,
    update_session,
    get_session_summary,
    create_session,
)
from app.api.rjm.schemas import ChatMessage


class TestModeDetection:
    """Test mode detection from user language."""

    def test_trader_mode_cpm(self):
        """Trader mode detects CPM terminology."""
        assert _detect_mode("What's the CPM looking like?") == "trader"

    def test_trader_mode_dsp(self):
        """Trader mode detects DSP terminology."""
        assert _detect_mode("I'll run this through DV360") == "trader"
        assert _detect_mode("Using TTD for this campaign") == "trader"

    def test_trader_mode_deal_id(self):
        """Trader mode detects deal ID terminology."""
        assert _detect_mode("Need the deal IDs for this") == "trader"
        assert _detect_mode("Set up a PMP deal") == "trader"

    def test_trader_mode_inventory(self):
        """Trader mode detects inventory/supply terminology."""
        assert _detect_mode("What's the inventory availability?") == "trader"
        assert _detect_mode("Need programmatic scale") == "trader"

    def test_smb_mode_small_business(self):
        """SMB mode detects small business language."""
        assert _detect_mode("I run a small business") == "smb"
        assert _detect_mode("This is for my shop") == "smb"

    def test_smb_mode_local_business(self):
        """SMB mode detects local business types."""
        assert _detect_mode("Marketing for my restaurant") == "smb"
        assert _detect_mode("Ads for my salon") == "smb"
        assert _detect_mode("My bakery needs customers") == "smb"

    def test_founder_mode(self):
        """Founder mode detects startup/founder language."""
        assert _detect_mode("I'm a founder building a new product") == "founder"
        assert _detect_mode("My company is in Series A") == "founder"
        assert _detect_mode("We're a startup looking to scale") == "founder"

    def test_planner_mode(self):
        """Planner mode detects strategic/cultural language."""
        assert _detect_mode("What's the cultural tension here?") == "planner"
        assert _detect_mode("Help me with audience segmentation") == "planner"
        assert _detect_mode("Need consumer behavior insights") == "planner"

    def test_creative_mode(self):
        """Creative mode detects narrative/storytelling language."""
        assert _detect_mode("Working on the brand narrative") == "creative"
        assert _detect_mode("Need help with storytelling") == "creative"
        assert _detect_mode("What's the campaign concept?") == "creative"
        assert _detect_mode("Developing the brand voice") == "creative"

    def test_no_mode_detected(self):
        """No mode when language is generic."""
        assert _detect_mode("I want to advertise my product") is None
        assert _detect_mode("Help me reach customers") is None
        assert _detect_mode("") is None
        assert _detect_mode(None) is None


class TestModeStying:
    """Test mode-aware response styling."""

    def test_trader_mode_no_additions(self):
        """Trader mode keeps reply tight with no additions."""
        reply = "Here's the plan."
        result = _apply_mode_styling(reply, "trader")
        assert result == reply

    def test_smb_mode_adds_plain_language(self):
        """SMB mode adds plain language explanation."""
        reply = "Here's the plan."
        result = _apply_mode_styling(reply, "smb")
        assert "simple version" in result.lower() or "ready-to-run plan" in result.lower()
        assert len(result) > len(reply)

    def test_planner_mode_adds_cultural_framing(self):
        """Planner mode adds cultural/strategic framing."""
        reply = "Here's the plan."
        result = _apply_mode_styling(reply, "planner")
        assert "cultural insight" in result.lower() or "behavioral tensions" in result.lower()

    def test_creative_mode_adds_narrative_framing(self):
        """Creative mode adds narrative emphasis."""
        reply = "Here's the plan."
        result = _apply_mode_styling(reply, "creative")
        assert "narrative" in result.lower() or "creative" in result.lower()

    def test_founder_mode_adds_efficiency_framing(self):
        """Founder mode adds efficiency/growth framing."""
        reply = "Here's the plan."
        result = _apply_mode_styling(reply, "founder")
        assert "efficiency" in result.lower() or "scale" in result.lower() or "cac" in result.lower()

    def test_no_mode_no_change(self):
        """No mode means no change to reply."""
        reply = "Here's the plan."
        assert _apply_mode_styling(reply, None) == reply


class TestInputClassification:
    """Test input classification for routing."""

    def test_activation_request_detected(self):
        """Activation requests are detected."""
        assert _classify_input_label("Let's activate this") == "request_activation"
        assert _classify_input_label("Map activation") == "request_activation"
        assert _classify_input_label("Need deal IDs") == "request_activation"

    def test_complete_input_default(self):
        """Default classification is complete."""
        assert _classify_input_label("Here's my brief") == "complete"
        assert _classify_input_label("Brand is Nike") == "complete"


class TestMessageExtraction:
    """Test message extraction helpers."""

    def test_get_last_user_message(self):
        """Last user message is extracted correctly."""
        messages = [
            ChatMessage(role="user", content="Hello"),
            ChatMessage(role="assistant", content="Hi there"),
            ChatMessage(role="user", content="Final message"),
        ]
        assert _get_last_user_message(messages) == "Final message"

    def test_get_last_user_message_empty(self):
        """Empty list returns empty string."""
        assert _get_last_user_message([]) == ""

    def test_get_last_user_message_only_assistant(self):
        """Only assistant messages returns empty string."""
        messages = [
            ChatMessage(role="assistant", content="Hi there"),
        ]
        assert _get_last_user_message(messages) == ""


class TestSessionManagement:
    """Test session state management."""

    def test_create_session(self):
        """Session creation returns valid UUID."""
        sid = create_session()
        assert sid is not None
        assert len(sid) == 36  # UUID format

    def test_get_session_creates_new(self):
        """get_session creates new session when none exists."""
        sid, state = get_session(None)
        assert sid is not None
        assert state is not None
        assert isinstance(state, SessionState)

    def test_get_session_returns_existing(self):
        """get_session returns existing session."""
        sid1 = create_session()
        sid2, state = get_session(sid1)
        assert sid1 == sid2

    def test_update_session_updates_fields(self):
        """update_session updates session fields."""
        sid = create_session()
        update_session(sid, brand_name="TestBrand", brief="Test brief")

        _, state = get_session(sid)
        assert state.brand_name == "TestBrand"
        assert state.brief == "Test brief"

    def test_update_session_ignores_none(self):
        """update_session ignores None values."""
        sid = create_session()
        update_session(sid, brand_name="TestBrand")
        update_session(sid, brand_name=None, brief="Test brief")

        _, state = get_session(sid)
        assert state.brand_name == "TestBrand"  # Not overwritten
        assert state.brief == "Test brief"

    def test_session_summary(self):
        """Session summary returns expected fields."""
        sid = create_session()
        update_session(sid, brand_name="TestBrand", brief="Test brief")

        summary = get_session_summary(sid)
        assert summary["session_id"] == sid
        assert summary["brand_name"] == "TestBrand"
        assert "turn_count" in summary
        assert "created_at" in summary


class TestStateTransitions:
    """Test chat state transition logic."""

    def test_valid_state_constants(self):
        """All state constants are defined."""
        assert GREETING_STATE == "STATE_GREETING"
        assert INPUT_STATE == "STATE_INPUT"
        assert CLARIFICATION_STATE == "STATE_CLARIFICATION"
        assert PROGRAM_GENERATION_STATE == "STATE_PROGRAM_GENERATION"
        assert REASONING_BRIDGE_STATE == "STATE_REASONING_BRIDGE"
        assert ACTIVATION_STATE == "STATE_ACTIVATION"
        assert EXIT_STATE == "STATE_EXIT"
        assert OPTIMIZATION_STATE == "STATE_OPTIMIZATION"

    def test_greeting_to_input_transition(self):
        """Greeting state should transition to Input."""
        # This tests the expected flow, actual handler testing requires mocks
        pass  # Requires full integration test with mocked LLM

    def test_input_to_clarification_when_missing_info(self):
        """Input state should go to Clarification when info missing."""
        pass  # Requires full integration test with mocked LLM

    def test_clarification_to_program_generation(self):
        """Clarification should go to Program Generation when info complete."""
        pass  # Requires full integration test with mocked LLM


class TestSessionState:
    """Test SessionState dataclass functionality."""

    def test_session_state_defaults(self):
        """SessionState has correct defaults."""
        state = SessionState()
        assert state.brand_name is None
        assert state.brief is None
        assert state.current_state == "STATE_GREETING"
        assert state.turn_count == 0
        assert state.activation_plan_generated is False
        assert state.program_generated is False

    def test_session_touch_increments_turn(self):
        """touch() increments turn count."""
        state = SessionState()
        assert state.turn_count == 0
        state.touch()
        assert state.turn_count == 1
        state.touch()
        assert state.turn_count == 2

    def test_session_expiry(self):
        """Session expiry works correctly."""
        from datetime import datetime, timezone, timedelta

        state = SessionState()
        state.last_activity = datetime.now(timezone.utc) - timedelta(minutes=120)

        assert state.is_expired(ttl_minutes=60) is True
        assert state.is_expired(ttl_minutes=180) is False
