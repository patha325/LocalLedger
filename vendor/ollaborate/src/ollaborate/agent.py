from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from ollama import AsyncClient
from pydantic import BaseModel

from .events import Event, EventHandler

T = TypeVar("T", bound=BaseModel)


@dataclass(slots=True)
class Agent:
    """One Ollama-backed specialist with an optional bounded tool loop."""

    name: str
    role: str
    model: str = "qwen3:8b"
    instructions: str = ""
    tools: list[Callable[..., Any]] = field(default_factory=list)
    options: dict[str, Any] = field(default_factory=dict)
    max_tool_rounds: int = 6

    async def run(
        self,
        task: str,
        *,
        context: str | None = None,
        output_type: type[T] | None = None,
        client: AsyncClient | None = None,
        on_event: EventHandler | None = None,
    ) -> str | T:
        client = client or AsyncClient()
        emit = on_event or (lambda event: None)
        emit(Event("agent_start", self.name, {"task": task, "model": self.model}))
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt()},
            {"role": "user", "content": self._user_prompt(task, context)},
        ]
        tool_map = {tool.__name__: tool for tool in self.tools}
        schema = output_type.model_json_schema() if output_type else None

        try:
            for round_number in range(self.max_tool_rounds + 1):
                response = await client.chat(
                    model=self.model,
                    messages=messages,
                    tools=self.tools or None,
                    format=schema,
                    options=self.options or None,
                )
                message = response.message
                calls = message.tool_calls or []
                if not calls:
                    content = message.content
                    result: str | T = (
                        output_type.model_validate_json(content) if output_type else content
                    )
                    emit(Event("agent_end", self.name, {"result": content}))
                    return result
                if round_number == self.max_tool_rounds:
                    raise RuntimeError(f"Agent {self.name!r} exceeded max_tool_rounds")
                messages.append(message.model_dump(exclude_none=True))
                for call in calls:
                    function = call.function
                    if function.name not in tool_map:
                        raise ValueError(f"Agent requested unknown tool: {function.name}")
                    arguments = dict(function.arguments or {})
                    emit(
                        Event(
                            "tool_call", self.name, {"tool": function.name, "arguments": arguments}
                        )
                    )
                    value = tool_map[function.name](**arguments)
                    if inspect.isawaitable(value):
                        value = await value
                    serialized = value if isinstance(value, str) else json.dumps(value, default=str)
                    emit(
                        Event(
                            "tool_result", self.name, {"tool": function.name, "result": serialized}
                        )
                    )
                    messages.append(
                        {"role": "tool", "tool_name": function.name, "content": serialized}
                    )
        except Exception as exc:
            emit(Event("error", self.name, {"error": str(exc)}))
            raise

        raise RuntimeError("Unreachable agent state")

    def _system_prompt(self) -> str:
        extra = f"\n\n{self.instructions.strip()}" if self.instructions.strip() else ""
        return (
            f"You are {self.name}, a specialist acting as {self.role}. "
            f"Be accurate and concise.{extra}"
        )

    @staticmethod
    def _user_prompt(task: str, context: str | None) -> str:
        if not context:
            return task
        return f"Task:\n{task}\n\nContext from the team:\n{context}"
