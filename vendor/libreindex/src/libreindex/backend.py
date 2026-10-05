"""Ollama adapter kept behind a tiny protocol for testing and extension."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import httpx


class Backend(Protocol):
    def embed(self, texts: Sequence[str], model: str) -> list[list[float]]: ...

    def generate(self, prompt: str, model: str) -> str: ...


class OllamaBackend:
    """Local Ollama generation and embedding backend."""

    def __init__(self, host: str = "http://127.0.0.1:11434") -> None:
        self.client = httpx.Client(base_url=host, timeout=120.0, trust_env=False)

    def embed(self, texts: Sequence[str], model: str) -> list[list[float]]:
        response = self._post("/api/embed", {"model": model, "input": list(texts)})
        embeddings = response.json()["embeddings"]
        return [list(vector) for vector in embeddings]

    def generate(self, prompt: str, model: str) -> str:
        response = self._post(
            "/api/chat",
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": 0.1},
                "stream": False,
            },
        )
        return str(response.json()["message"]["content"]).strip()

    def _post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        try:
            response = self.client.post(path, json=payload)
            response.raise_for_status()
            return response
        except httpx.ConnectError as error:
            raise RuntimeError(
                "Could not connect to Ollama. Start Ollama and verify the configured host."
            ) from error
        except httpx.HTTPStatusError as error:
            detail = error.response.text[:500]
            raise RuntimeError(f"Ollama request failed: {detail}") from error
