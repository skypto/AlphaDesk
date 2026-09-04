from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol, TypeVar, cast

from openai import AsyncOpenAI
from pydantic import BaseModel

ResponseT = TypeVar("ResponseT", bound=BaseModel)


class StructuredOutputError(ValueError):
    """The provider returned content that was not a schema-valid JSON document."""


def _decode_structured_content(content: str) -> object:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        if first_newline >= 0:
            cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise StructuredOutputError("Provider returned malformed structured output") from error


class AIProvider(Protocol):
    name: str
    model: str

    async def generate(
        self,
        *,
        agent_name: str,
        instructions: str,
        input_payload: str,
        response_model: type[ResponseT],
    ) -> ResponseT: ...


class FixtureAIProvider:
    name = "fixture"
    model = "deterministic-v1"

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    async def generate(
        self,
        *,
        agent_name: str,
        instructions: str,
        input_payload: str,
        response_model: type[ResponseT],
    ) -> ResponseT:
        del instructions, input_payload
        if agent_name not in self._responses:
            raise RuntimeError(f"Fixture unavailable for {agent_name}")
        return response_model.model_validate(self._responses[agent_name])


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "gpt-5.4-mini",
        timeout_seconds: float = 20,
        client: Any | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required for the OpenAI provider")
        self.model = model
        self._timeout = timeout_seconds
        self._client = client or AsyncOpenAI(
            api_key=api_key, timeout=timeout_seconds, max_retries=0
        )

    async def generate(
        self,
        *,
        agent_name: str,
        instructions: str,
        input_payload: str,
        response_model: type[ResponseT],
    ) -> ResponseT:
        response = await asyncio.wait_for(
            self._client.responses.parse(
                model=self.model,
                instructions=instructions,
                input=input_payload,
                text_format=response_model,
                max_output_tokens=1200,
                tools=[],
                tool_choice="none",
                store=False,
                metadata={"agent": agent_name},
            ),
            timeout=self._timeout,
        )
        parsed = cast(ResponseT | None, response.output_parsed)
        if parsed is None:
            raise ValueError(f"{agent_name} returned no structured output")
        return parsed


class OpenRouterProvider:
    """Read-only, schema-constrained OpenRouter adapter with no tool access."""

    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        *,
        model: str,
        timeout_seconds: float = 20,
        client: Any | None = None,
    ) -> None:
        if not api_key or not model:
            raise ValueError("OpenRouter API key and model are required")
        self.model = model
        self._timeout = timeout_seconds
        self._client = client or AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout=timeout_seconds,
            max_retries=0,
            default_headers={"X-Title": "AlphaDesk"},
        )

    async def generate(
        self,
        *,
        agent_name: str,
        instructions: str,
        input_payload: str,
        response_model: type[ResponseT],
    ) -> ResponseT:
        schema_name = "".join(character for character in agent_name if character.isalnum())[:48]
        response = await asyncio.wait_for(
            self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": instructions + "\nReturn only the required JSON object.",
                    },
                    {"role": "user", "content": input_payload},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema_name or "AlphaDeskResponse",
                        "strict": True,
                        "schema": response_model.model_json_schema(),
                    },
                },
                max_tokens=2000,
                temperature=0,
                extra_body={
                    "provider": {"require_parameters": True},
                    "plugins": [{"id": "response-healing"}],
                },
            ),
            timeout=self._timeout,
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError(f"{agent_name} returned no structured output")
        return response_model.model_validate(_decode_structured_content(content))
