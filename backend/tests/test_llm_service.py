"""LLM service: prompt plumbing, JSON parsing, and fallbacks.

The Groq client is stubbed; no network calls. These tests lock in both the
happy path (well-formed JSON from the model) and the degradation behavior
(no key configured, malformed model output).
"""
import json
from types import SimpleNamespace

import pytest

from app.services.llm_service import LLMService


pytestmark = pytest.mark.unit


class FakeGroqClient:
    """Minimal stand-in for groq.Groq supporting chat.completions.create."""

    def __init__(self, content: str):
        self._content = content
        self.last_kwargs = None

        def create(**kwargs):
            self.last_kwargs = kwargs
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))],
                usage=SimpleNamespace(total_tokens=123),
            )

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


@pytest.fixture
def service():
    return LLMService()


class TestAvailability:
    def test_unavailable_without_key(self, service):
        assert service.client is None
        assert service.is_available() is False


class TestTradeAnalysis:
    async def test_fallback_without_llm(self, service):
        result = await service.analyze_trade([{"name": "A"}], [{"name": "B"}], [], [], {})
        assert result["overall_verdict"] == "manual_review"
        assert result["fairness_score"] == 50.0

    async def test_parses_llm_json(self, service):
        payload = {
            "overall_verdict": "accept",
            "fairness_score": 71,
            "value_difference": 4.2,
            "analysis_summary": "Good trade.",
            "pros": ["More points"],
            "cons": [],
            "recommendations": ["Do it"],
            "risk_assessment": "Low",
            "team_fit_analysis": "Fills RB hole",
        }
        service.client = FakeGroqClient(json.dumps(payload))
        result = await service.analyze_trade([{"name": "A"}], [{"name": "B"}], [], [], {})
        assert result["overall_verdict"] == "accept"
        assert result["fairness_score"] == 71

    async def test_malformed_json_falls_back(self, service):
        service.client = FakeGroqClient("definitely not json {")
        result = await service.analyze_trade([{"name": "A"}], [{"name": "B"}], [], [], {})
        assert result["overall_verdict"] == "manual_review"


class TestSuggestions:
    async def test_fallback_without_llm(self, service):
        suggestions = await service.generate_strategic_suggestions([], {}, [])
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "lineup"

    async def test_parses_and_assigns_ids(self, service):
        payload = {
            "suggestions": [
                {"type": "pickup", "priority": "high", "title": "Get X",
                 "description": "d", "reasoning": "r", "potential_impact": "p",
                 "confidence_score": 0.9, "action_details": {}},
                {"type": "drop", "priority": "low", "title": "Drop Y",
                 "description": "d", "reasoning": "r", "potential_impact": "p",
                 "confidence_score": 0.4, "action_details": {}},
            ]
        }
        service.client = FakeGroqClient(json.dumps(payload))
        suggestions = await service.generate_strategic_suggestions(
            [{"full_name": "QB Guy"}], {"name": "Lg"}, []
        )
        assert [s["id"] for s in suggestions] == ["1", "2"]

    async def test_malformed_json_falls_back(self, service):
        service.client = FakeGroqClient("[broken")
        suggestions = await service.generate_strategic_suggestions([], {}, [])
        assert suggestions[0]["title"] == "Review Your Lineup"


class TestDraftAdvice:
    async def test_fallback_recommends_top_vbd(self, service):
        board = [
            {"name": "Best Player", "position": "RB", "vbd": 80, "projected_points": 280},
            {"name": "Second", "position": "WR", "vbd": 70, "projected_points": 260},
            {"name": "Third", "position": "QB", "vbd": 60, "projected_points": 350},
        ]
        result = await service.analyze_draft_pick(1, [], {}, board, "ppr")
        assert result["recommended_player"] == "Best Player"
        assert result["alternatives"] == ["Second", "Third"]

    async def test_fallback_empty_board(self, service):
        result = await service.analyze_draft_pick(1, [], {}, [], "ppr")
        assert result["recommended_player"] is None

    async def test_parses_llm_json(self, service):
        payload = {
            "recommended_player": "LLM Pick",
            "alternatives": ["Alt"],
            "reasoning": "Value.",
            "strategy_note": "Go RB next.",
        }
        service.client = FakeGroqClient(json.dumps(payload))
        result = await service.analyze_draft_pick(
            3, [{"name": "Someone"}], {"RB": 1}, [{"name": "X"}], "ppr"
        )
        assert result["recommended_player"] == "LLM Pick"


class TestLineupOptimization:
    async def test_unavailable_returns_empty(self, service):
        result = await service.analyze_lineup_optimization([], {}, {}, {})
        assert result["recommendations"] == []

    async def test_parses_llm_json(self, service):
        payload = {"recommendations": [{"change": "Start X over Y"}],
                   "reasoning": "matchup", "projected_impact": 5.5}
        service.client = FakeGroqClient(json.dumps(payload))
        result = await service.analyze_lineup_optimization([], {}, {}, {})
        assert result["projected_impact"] == 5.5
