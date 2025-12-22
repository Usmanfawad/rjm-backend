"""
Tests for MIRA Activation and Reasoning Engine.

Covers:
- Reasoning Engine funnel determination
- Media mix calculation
- Platform path selection
- Activation plan generation
- Optimization suggestions
"""

import pytest

from app.services.mira_reasoning_engine import (
    run_reasoning_engine,
    ReasoningContext,
    _infer_category_from_brief,
    _determine_funnel_stage,
    _determine_media_mix,
    _determine_platform_path,
    _determine_budget_window,
    _determine_pacing_mode,
    _determine_flighting_cadence,
    _determine_performance_path,
    CATEGORY_PROFILES,
    KPI_FUNNEL_MAP,
    MIX_TEMPLATES,
)
from app.services.mira_activation import (
    build_activation_plan,
    format_activation_summary_block,
    suggest_downstream_optimization,
    infer_platform_path,
    default_budget_window,
    default_pacing_mode,
    default_flighting_cadence,
    ActivationPlan,
    OptimizationSuggestion,
)


class TestCategoryInference:
    """Test category inference from brief text."""

    def test_qsr_category(self):
        """QSR category detected from restaurant keywords."""
        assert _infer_category_from_brief("family restaurant launching brunch", "BrunchBox") == "QSR"
        assert _infer_category_from_brief("fast food chain promotion", "McBurger") == "QSR"

    def test_auto_category(self):
        """Auto category detected from vehicle keywords."""
        assert _infer_category_from_brief("new SUV launch campaign", "Ford") == "Auto"
        assert _infer_category_from_brief("electric vehicle awareness", "Tesla") == "Auto"

    def test_beauty_category(self):
        """Beauty category detected from cosmetic keywords."""
        assert _infer_category_from_brief("skincare line launch", "Glossier") == "Beauty"
        assert _infer_category_from_brief("makeup tutorial campaign", "MAC") == "Beauty"

    def test_finance_category(self):
        """Finance category detected from banking keywords."""
        assert _infer_category_from_brief("bank account promotion", "Chase") == "Finance"
        assert _infer_category_from_brief("insurance awareness", "Geico") == "Finance"

    def test_retail_default(self):
        """Retail is default when no specific category detected."""
        assert _infer_category_from_brief("product launch campaign", "AcmeCorp") == "Retail"


class TestFunnelDetermination:
    """Test funnel stage determination."""

    def test_kpi_determines_funnel(self):
        """KPI explicitly sets funnel stage."""
        ctx = ReasoningContext(brand_name="Test", brief="Campaign", kpi="reach")
        assert _determine_funnel_stage(ctx) == "upper"

        ctx = ReasoningContext(brand_name="Test", brief="Campaign", kpi="conversion")
        assert _determine_funnel_stage(ctx) == "lower"

        ctx = ReasoningContext(brand_name="Test", brief="Campaign", kpi="engagement")
        assert _determine_funnel_stage(ctx) == "mid"

    def test_brief_cues_funnel(self):
        """Brief language affects funnel stage."""
        ctx = ReasoningContext(brand_name="Test", brief="brand awareness campaign launch")
        assert _determine_funnel_stage(ctx) == "upper"

        ctx = ReasoningContext(brand_name="Test", brief="drive purchase conversions")
        assert _determine_funnel_stage(ctx) == "lower"

    def test_category_bias_funnel(self):
        """Category profile affects funnel when no KPI."""
        ctx = ReasoningContext(brand_name="Test", brief="beauty campaign", category="Beauty")
        # Beauty has upper funnel bias
        assert _determine_funnel_stage(ctx) == "upper"


class TestMediaMix:
    """Test media mix determination."""

    def test_upper_funnel_mix(self):
        """Upper funnel has CTV-heavy mix."""
        # Use QSR category which has CTV-heavy bias to ensure CTV prominence
        ctx = ReasoningContext(
            brand_name="Test",
            brief="brand awareness campaign",
            funnel_stage="upper",
            category="QSR"  # QSR has CTV-heavy mix bias
        )
        mix = _determine_media_mix(ctx)
        # QSR + upper funnel should result in high CTV
        ctv_val = mix["CTV"]
        assert any(pct in ctv_val for pct in ["50", "55", "60", "65"])

    def test_lower_funnel_mix(self):
        """Lower funnel has Display-heavy mix."""
        ctx = ReasoningContext(brand_name="Test", brief="conversions", funnel_stage="lower")
        mix = _determine_media_mix(ctx)
        assert "20" in mix["Display"] or "25" in mix["Display"] or "30" in mix["Display"]

    def test_creative_angle_affects_mix(self):
        """Creative angle modifies mix."""
        ctx = ReasoningContext(
            brand_name="Test",
            brief="campaign",
            funnel_stage="mid",
            creative_angle="emotional storytelling"
        )
        mix = _determine_media_mix(ctx)
        # Emotional storytelling should push toward CTV
        assert "55" in mix["CTV"] or "60" in mix["CTV"] or "65" in mix["CTV"]


class TestPlatformPath:
    """Test platform path selection."""

    def test_explicit_dsp_preference(self):
        """Explicit DSP preference is respected."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", platform_preference="DSP")
        assert _determine_platform_path(ctx) == "DSP"

    def test_urgent_timeline_direct(self):
        """Urgent timeline routes to Direct."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", timeline="need this in 24 hours")
        assert _determine_platform_path(ctx) == "Direct via RJM"

    def test_high_budget_hybrid(self):
        """High budget suggests Hybrid."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", budget=150000)
        assert _determine_platform_path(ctx) == "Hybrid"

    def test_low_budget_dsp(self):
        """Low budget routes to DSP."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", budget=30000)
        assert _determine_platform_path(ctx) == "DSP"


class TestBudgetWindow:
    """Test budget window determination."""

    def test_low_budget_single_window(self):
        """Low budget gets single window."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", budget=30000)
        assert _determine_budget_window(ctx) == "single"

    def test_high_budget_split_window(self):
        """High budget gets split window."""
        ctx = ReasoningContext(brand_name="Test", brief="campaign", budget=150000)
        assert _determine_budget_window(ctx) == "split"

    def test_brief_cues_window(self):
        """Brief language affects window."""
        ctx = ReasoningContext(brand_name="Test", brief="multiple waves of activity")
        assert _determine_budget_window(ctx) == "split"

        ctx = ReasoningContext(brand_name="Test", brief="always-on strategy")
        assert _determine_budget_window(ctx) == "adaptive"


class TestReasoningEngine:
    """Test full Reasoning Engine flow."""

    def test_reasoning_engine_basic(self):
        """Reasoning engine returns complete context."""
        ctx = run_reasoning_engine(
            brand_name="BrunchBox",
            brief="Family-focused QSR launching weekend brunch with neighborhood storytelling"
        )

        assert ctx.brand_name == "BrunchBox"
        assert ctx.category == "QSR"
        assert ctx.funnel_stage in ("upper", "mid", "lower")
        assert ctx.platform_path in ("DSP", "Direct via RJM", "Hybrid")
        assert ctx.budget_window in ("single", "split", "adaptive")
        assert ctx.media_mix is not None
        assert ctx.strategic_rationale != ""
        assert ctx.current_state == "STATE_PRE_ACTIVATION"

    def test_reasoning_engine_with_kpi(self):
        """Reasoning engine respects KPI."""
        ctx = run_reasoning_engine(
            brand_name="TestBrand",
            brief="Drive conversions",
            kpi="CPA"
        )
        assert ctx.funnel_stage == "lower"
        assert ctx.performance_path == "quality"

    def test_reasoning_engine_missing_inputs(self):
        """Reasoning engine handles missing inputs."""
        ctx = run_reasoning_engine(brand_name="", brief="")
        assert "brand_name" in ctx.missing_inputs
        assert ctx.current_state == "STATE_CLARIFICATION"


class TestActivationPlan:
    """Test activation plan generation."""

    def test_build_activation_plan_basic(self):
        """Activation plan builds with basic inputs."""
        plan = build_activation_plan(
            brand_name="TestBrand",
            brief="Test campaign for awareness"
        )

        assert isinstance(plan, ActivationPlan)
        assert plan.platform_path in ("DSP", "Direct via RJM", "Hybrid")
        assert plan.budget_window in ("single", "split", "adaptive")
        assert plan.pacing_mode in ("standard", "front-loaded", "back-loaded")
        assert plan.flighting_cadence in ("linear", "pulsed", "burst")
        assert plan.persona_deployment != ""
        assert plan.channel_deployment != ""
        assert plan.activation_rationale != ""

    def test_build_activation_plan_with_dsp(self):
        """Activation plan respects DSP preference."""
        plan = build_activation_plan(
            brand_name="TestBrand",
            brief="Campaign",
            user_text="Using DV360 for this"
        )
        assert plan.platform_path == "DSP"
        assert "DSP-ready" in plan.deal_id_or_packaging

    def test_activation_plan_funnel_affects_deployment(self):
        """Funnel stage affects persona deployment."""
        plan = build_activation_plan(
            brand_name="TestBrand",
            brief="Brand awareness launch",
            kpi="reach"
        )
        # Upper funnel should emphasize CTV
        assert "CTV" in plan.persona_deployment

    def test_format_activation_summary(self):
        """Activation summary formats correctly."""
        plan = ActivationPlan(
            platform_path="Direct via RJM",
            budget_window="single",
            pacing_mode="standard",
            flighting_cadence="linear",
            persona_deployment="Primary to CTV",
            channel_deployment="CTV-heavy",
            deal_id_or_packaging="Package as Direct",
            activation_rationale="Clean awareness launch"
        )

        summary = format_activation_summary_block(plan)
        assert "Campaign Activation Summary" in summary
        assert "Direct via RJM" in summary
        assert "Single" in summary
        assert "Standard" in summary

    def test_format_activation_summary_with_reasoning(self):
        """Activation summary includes reasoning when requested."""
        plan = ActivationPlan(
            platform_path="Direct via RJM",
            budget_window="single",
            pacing_mode="standard",
            flighting_cadence="linear",
            persona_deployment="Primary to CTV",
            channel_deployment="CTV-heavy",
            deal_id_or_packaging="Package as Direct",
            activation_rationale="Clean awareness launch",
            funnel_stage="upper",
            media_mix={"CTV": "50%", "OLV": "30%"},
            performance_path="balanced"
        )

        summary = format_activation_summary_block(plan, include_reasoning=True)
        assert "Reasoning Context" in summary
        assert "Funnel Stage" in summary
        assert "Media Mix" in summary


class TestOptimizationSuggestions:
    """Test downstream optimization suggestions."""

    def test_scale_optimization(self):
        """Scale request returns scale suggestion."""
        suggestion = suggest_downstream_optimization("We need more scale")
        assert isinstance(suggestion, OptimizationSuggestion)
        assert "widen" in suggestion.move.lower() or "scale" in suggestion.move.lower()

    def test_quality_optimization(self):
        """Quality request returns quality suggestion."""
        suggestion = suggest_downstream_optimization("Need higher quality leads")
        assert "tighten" in suggestion.move.lower() or "quality" in suggestion.move.lower()

    def test_under_delivery_optimization(self):
        """Under-delivery request returns delivery suggestion."""
        suggestion = suggest_downstream_optimization("Campaign is under-delivering")
        assert "olv" in suggestion.move.lower() or "display" in suggestion.move.lower()

    def test_frequency_optimization(self):
        """Over-frequency request returns frequency suggestion."""
        suggestion = suggest_downstream_optimization("Too much frequency, ads showing too often")
        assert "ease" in suggestion.move.lower() or "spread" in suggestion.move.lower()

    def test_geo_optimization(self):
        """Geo request returns DMA suggestion."""
        suggestion = suggest_downstream_optimization("Some DMAs are weak")
        assert "dma" in suggestion.move.lower() or "geo" in suggestion.move.lower()

    def test_default_optimization(self):
        """Unknown request returns balanced suggestion."""
        suggestion = suggest_downstream_optimization("Something else entirely")
        assert suggestion.move != ""
        assert suggestion.rationale != ""
        assert suggestion.next_step != ""


class TestLegacyFunctions:
    """Test legacy/compatibility functions."""

    def test_infer_platform_path_dsp(self):
        """Legacy platform inference detects DSP."""
        assert infer_platform_path("Using DV360") == "DSP"
        assert infer_platform_path("TTD campaign") == "DSP"

    def test_infer_platform_path_direct(self):
        """Legacy platform inference defaults to Direct."""
        assert infer_platform_path("regular campaign") == "Direct via RJM"
        assert infer_platform_path(None) == "Direct via RJM"

    def test_default_functions(self):
        """Legacy default functions return expected values."""
        assert default_budget_window() == "single"
        assert default_pacing_mode() == "standard"
        assert default_flighting_cadence() == "linear"
