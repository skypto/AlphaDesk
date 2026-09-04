from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from packages.ai.prompts import (
    CONTEXT_PROMPT,
    CONTEXT_VERSION,
    DECISION_COMPOSER_VERSION,
    DECISION_PROMPT,
    DEVILS_ADVOCATE_PROMPT,
    DEVILS_ADVOCATE_VERSION,
)
from packages.ai.provider import AIProvider
from packages.domain.ai import (
    AIContextReport,
    AIWorkflowResult,
    DecisionReport,
    DevilsAdvocateReport,
    Recommendation,
)

OutputT = TypeVar("OutputT", bound=BaseModel)


class AIWorkflow:
    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    async def _with_repair(
        self,
        *,
        agent_name: str,
        instructions: str,
        payload: dict[str, object],
        response_model: type[OutputT],
        allowed_source_ids: frozenset[str],
    ) -> OutputT:
        input_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        first_error: Exception | None = None
        for attempt in range(2):
            try:
                repair = (
                    "\nPrevious output failed validation. Strictly repair to the schema."
                    if attempt
                    else ""
                )
                result = await self._provider.generate(
                    agent_name=agent_name,
                    instructions=instructions + repair,
                    input_payload=input_payload,
                    response_model=response_model,
                )
                citations = getattr(result, "citations", ())
                if not citations:
                    raise ValueError(f"{agent_name} returned no citations")
                unknown = {citation.source_id for citation in citations} - allowed_source_ids
                if unknown:
                    raise ValueError(f"{agent_name} cited unknown sources: {sorted(unknown)}")
                return result
            except Exception as error:
                first_error = error
        assert first_error is not None
        raise first_error

    async def run(self, evidence: dict[str, object]) -> AIWorkflowResult:
        raw_sources = evidence.get("sources", ())
        sources = raw_sources if isinstance(raw_sources, (list, tuple)) else ()
        allowed_source_ids = frozenset(
            str(item["source_id"])
            for item in sources
            if isinstance(item, dict) and item.get("source_id")
        )
        versions = {
            "context": CONTEXT_VERSION,
            "devils_advocate": DEVILS_ADVOCATE_VERSION,
            "decision": DECISION_COMPOSER_VERSION,
        }
        try:
            context = await self._with_repair(
                agent_name="ai_context",
                instructions=CONTEXT_PROMPT,
                payload={"evidence": evidence},
                response_model=AIContextReport,
                allowed_source_ids=allowed_source_ids,
            )
            devil = await self._with_repair(
                agent_name="devils_advocate",
                instructions=DEVILS_ADVOCATE_PROMPT,
                payload={"evidence": evidence, "context": context.model_dump(mode="json")},
                response_model=DevilsAdvocateReport,
                allowed_source_ids=allowed_source_ids,
            )
            decision = await self._with_repair(
                agent_name="decision_composer",
                instructions=DECISION_PROMPT,
                payload={
                    "evidence": evidence,
                    "context": context.model_dump(mode="json"),
                    "devils_advocate": devil.model_dump(mode="json"),
                },
                response_model=DecisionReport,
                allowed_source_ids=allowed_source_ids,
            )
            return AIWorkflowResult(
                provider=self._provider.name,
                model=self._provider.model,
                prompt_versions=versions,
                context=context,
                devils_advocate=devil,
                decision=decision,
            )
        except Exception as error:
            return AIWorkflowResult(
                provider=self._provider.name,
                model=self._provider.model,
                prompt_versions=versions,
                context=None,
                devils_advocate=None,
                decision=DecisionReport(
                    recommendation=Recommendation.NEEDS_MORE_DATA,
                    confidence=0,
                    facts=(),
                    interpretations=(),
                    reasons=(
                        "AI workflow unavailable; deterministic systems remain authoritative.",
                    ),
                    citations=(),
                ),
                degraded=True,
                failure_reason=type(error).__name__,
            )
