"""LLM generation backends."""

from __future__ import annotations

import os
from typing import Protocol

from rag_injection_lab.config import CHAT_MODEL, PROVIDER


class Generator(Protocol):
    model_name: str
    provider: str

    def complete(self, messages: list[dict[str, str]]) -> str: ...


class MockGenerator:
    """Offline generator: echoes retrieval context for tests / no-key demos."""

    def __init__(self, model_name: str = "mock-echo") -> None:
        self.model_name = model_name
        self.provider = "mock"

    def complete(self, messages: list[dict[str, str]]) -> str:
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        # Surface enough of the prompt for attack demos without a live LLM
        snippet = user[:1200]
        return (
            "[mock provider — no live LLM call]\n\n"
            "I would answer based on the following prompt content:\n\n"
            f"{snippet}"
            + ("…" if len(user) > 1200 else "")
        )


class OpenAIGenerator:
    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or CHAT_MODEL
        self.provider = "openai"

    def complete(self, messages: list[dict[str, str]]) -> str:
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()


class AnthropicGenerator:
    def __init__(self, model: str | None = None) -> None:
        self.model_name = model or os.environ.get("RAG_LAB_CHAT_MODEL", "claude-3-5-haiku-latest")
        self.provider = "anthropic"

    def complete(self, messages: list[dict[str, str]]) -> str:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic package not installed; pip install 'rag-injection-lab[anthropic]'"
            ) from exc

        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user_msgs = [m for m in messages if m["role"] != "system"]
        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=system or "You are a helpful assistant.",
            messages=[{"role": m["role"], "content": m["content"]} for m in user_msgs],
            temperature=0.2,
        )
        parts = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()


def get_generator(provider: str | None = None, model: str | None = None) -> Generator:
    prov = (provider or PROVIDER).lower()
    if prov in ("mock", "local", "hash"):
        return MockGenerator()
    if prov == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            return MockGenerator(model_name="mock-no-openai-key")
        return OpenAIGenerator(model=model)
    if prov == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return MockGenerator(model_name="mock-no-anthropic-key")
        return AnthropicGenerator(model=model)
    return MockGenerator()
