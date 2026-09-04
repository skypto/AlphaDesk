from __future__ import annotations

import json
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from packages.ai.provider import FixtureAIProvider, OpenAIProvider, OpenRouterProvider
from packages.ai.workflow import AIWorkflow
from packages.domain.ai import Recommendation

SOURCE = {"source_id": "fixture-market-1", "kind": "market", "content": "Synthetic data"}


def fixture_responses() -> dict[str, object]:
    citation = [{"source_id": SOURCE["source_id"], "claim": "Synthetic signal is confirmed."}]
    return {
        "ai_context": {
            "facts": ["Relative volume is 3.2."],
            "interpretations": ["Momentum confirms the catalyst."],
            "assumptions": ["Fixture timestamps are current."],
            "catalyst_summary": "Positive synthetic catalyst.",
            "signal_consistent": True,
            "confidence": "0.82",
            "reasons": ["Price and volume agree."],
            "citations": citation,
        },
        "devils_advocate": {
            "alternative_explanations": ["Broad market beta."],
            "priced_in_risk": "Moderate",
            "extension_risk": "Controlled by deterministic gap limit.",
            "contradictory_evidence": [],
            "portfolio_overlap": "None in fixture.",
            "liquidity_concerns": [],
            "reject_trade": False,
            "confidence": "0.70",
            "reasons": ["No decisive contradiction."],
            "citations": citation,
        },
        "decision_composer": {
            "recommendation": "PROCEED_TO_STRUCTURE_SELECTION",
            "confidence": "0.78",
            "facts": ["Deterministic signal passed."],
            "interpretations": ["Continuation remains plausible."],
            "reasons": ["Evidence is consistent and cited."],
            "citations": citation,
        },
    }


@pytest.mark.asyncio
async def test_versioned_ai_workflow_returns_strict_cited_recommendation() -> None:
    result = await AIWorkflow(FixtureAIProvider(fixture_responses())).run(
        {"sources": [SOURCE], "signal_score": 85.38}
    )

    assert not result.degraded
    assert result.decision.recommendation is Recommendation.PROCEED_TO_STRUCTURE_SELECTION
    assert result.prompt_versions == {
        "context": "ai-context-v1",
        "devils_advocate": "devils-advocate-v1",
        "decision": "decision-composer-v1",
    }


class InvalidProvider:
    name = "invalid"
    model = "fixture"

    def __init__(self) -> None:
        self.calls = 0

    async def generate(self, **kwargs: Any) -> Any:
        self.calls += 1
        response_model = kwargs["response_model"]
        return response_model.model_validate({"confidence": 2})


@pytest.mark.asyncio
async def test_malformed_ai_retries_once_then_degrades_safely() -> None:
    provider = InvalidProvider()
    result = await AIWorkflow(provider).run({"sources": [SOURCE]})

    assert provider.calls == 2
    assert result.degraded
    assert result.decision.recommendation is Recommendation.NEEDS_MORE_DATA
    assert result.failure_reason == "ValidationError"


@pytest.mark.asyncio
async def test_unknown_citations_are_rejected_and_degrade() -> None:
    responses = fixture_responses()
    context = responses["ai_context"]
    assert isinstance(context, dict)
    context["citations"] = [{"source_id": "invented", "claim": "Unsupported claim"}]
    result = await AIWorkflow(FixtureAIProvider(responses)).run({"sources": [SOURCE]})

    assert result.degraded
    assert result.failure_reason == "ValueError"


class FakeResponses:
    def __init__(self, parsed: object) -> None:
        self.parsed = parsed
        self.kwargs: dict[str, object] = {}

    async def parse(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        return SimpleNamespace(output_parsed=self.parsed)


@pytest.mark.asyncio
async def test_openai_provider_exposes_no_tools() -> None:
    from packages.domain.ai import AIContextReport

    parsed = AIContextReport.model_validate(fixture_responses()["ai_context"])
    responses = FakeResponses(parsed)
    client = SimpleNamespace(responses=responses)
    provider = OpenAIProvider("test", client=client)
    result = await provider.generate(
        agent_name="ai_context",
        instructions="versioned prompt",
        input_payload="{}",
        response_model=AIContextReport,
    )

    assert result == parsed
    assert responses.kwargs["tools"] == []
    assert responses.kwargs["tool_choice"] == "none"
    assert responses.kwargs["store"] is False


class FakeChatCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs: dict[str, object] = {}

    async def create(self, **kwargs: object) -> SimpleNamespace:
        self.kwargs = kwargs
        message = SimpleNamespace(content=self.content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


@pytest.mark.asyncio
async def test_openrouter_requires_structured_parameters_and_heals_json() -> None:
    from packages.domain.ai import AIContextReport

    content = "```json\n" + json.dumps(fixture_responses()["ai_context"]) + "\n```"
    completions = FakeChatCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenRouterProvider("test", model="test/model", client=client)

    result = await provider.generate(
        agent_name="ai_context",
        instructions="versioned prompt",
        input_payload="{}",
        response_model=AIContextReport,
    )

    assert result.confidence == Decimal("0.82")
    assert completions.kwargs["extra_body"] == {
        "provider": {"require_parameters": True},
        "plugins": [{"id": "response-healing"}],
    }
