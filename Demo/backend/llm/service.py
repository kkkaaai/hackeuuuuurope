"""LLM service — native OpenAI/Anthropic SDKs wrapped with Paid.ai for cost tracing."""

import asyncio
import json
import re

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    paid_api_key: str = ""
    default_provider: str = "openai"
    default_model: str = "gpt-4o"
    llm_temperature: float = 0.0
    model_config = {"env_file": ".env", "extra": "ignore"}


def get_client(provider: str | None = None):
    """Return a Paid.ai-wrapped LLM client for the given provider.

    Returns an OpenAI or Anthropic client wrapped with Paid.ai for
    automatic cost tracing. Falls back to unwrapped client if Paid.ai
    is not configured.
    """
    settings = Settings()
    p = provider or settings.default_provider

    if p == "openai":
        from openai import OpenAI

        raw_client = OpenAI(api_key=settings.openai_api_key)
        if settings.paid_api_key:
            try:
                from paid.tracing.wrappers import PaidOpenAI

                return PaidOpenAI(raw_client)
            except ImportError:
                pass
        return raw_client

    elif p == "anthropic":
        import anthropic

        raw_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        if settings.paid_api_key:
            try:
                from paid.tracing.wrappers import PaidAnthropic

                return PaidAnthropic(raw_client)
            except ImportError:
                pass
        return raw_client

    raise ValueError(f"Unknown provider: {p}")


async def call_llm(
    system: str,
    user: str,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Call an LLM and return the text response.

    Uses the native SDK for the chosen provider, wrapped with Paid.ai
    for cost tracking when available.
    """
    settings = Settings()
    p = provider or settings.default_provider
    m = model or settings.default_model

    if p == "openai":
        client = get_client("openai")

        def _call_openai():
            return client.chat.completions.create(
                model=m,
                temperature=settings.llm_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )

        response = await asyncio.to_thread(_call_openai)
        return response.choices[0].message.content or ""

    elif p == "anthropic":
        client = get_client("anthropic")

        def _call_anthropic():
            return client.messages.create(
                model=m,
                max_tokens=4096,
                temperature=settings.llm_temperature,
                system=system,
                messages=[{"role": "user", "content": user}],
            )

        response = await asyncio.to_thread(_call_anthropic)
        return response.content[0].text

    raise ValueError(f"Unknown provider: {p}")


async def call_llm_messages(
    messages: list[dict],
    provider: str | None = None,
    model: str | None = None,
) -> str:
    """Call an LLM with a full messages array for multi-turn conversation."""
    settings = Settings()
    p = provider or settings.default_provider
    m = model or settings.default_model

    if p == "openai":
        client = get_client("openai")

        def _call_openai():
            return client.chat.completions.create(
                model=m,
                temperature=settings.llm_temperature,
                messages=messages,
            )

        response = await asyncio.to_thread(_call_openai)
        return response.choices[0].message.content or ""

    elif p == "anthropic":
        client = get_client("anthropic")
        system_msg = ""
        conversation = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                conversation.append(msg)

        def _call_anthropic():
            kwargs = {
                "model": m,
                "max_tokens": 4096,
                "temperature": settings.llm_temperature,
                "messages": conversation,
            }
            if system_msg:
                kwargs["system"] = system_msg
            return client.messages.create(**kwargs)

        response = await asyncio.to_thread(_call_anthropic)
        return response.content[0].text

    raise ValueError(f"Unknown provider: {p}")


def parse_json_output(text: str, schema: dict | None = None) -> dict:
    """Extract the first JSON object from LLM text output."""
    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    return {"raw": text}
