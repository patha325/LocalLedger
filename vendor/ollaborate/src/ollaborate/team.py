from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

from ollama import AsyncClient

from .agent import Agent
from .events import EventHandler


@dataclass(frozen=True, slots=True)
class RunResult:
    output: str
    contributions: dict[str, list[str]] = field(default_factory=dict)


class Team:
    """Compose agents using predictable, inspectable orchestration patterns."""

    def __init__(
        self,
        *agents: Agent,
        client: AsyncClient | None = None,
        on_event: EventHandler | None = None,
    ) -> None:
        if not agents:
            raise ValueError("A team needs at least one agent")
        names = [agent.name for agent in agents]
        if len(names) != len(set(names)):
            raise ValueError("Agent names must be unique")
        self.agents = list(agents)
        self.client = client or AsyncClient()
        self.on_event = on_event

    async def pipeline(self, task: str) -> RunResult:
        context: str | None = None
        contributions: dict[str, list[str]] = {}
        for agent in self.agents:
            answer = await agent.run(
                task, context=context, client=self.client, on_event=self.on_event
            )
            text = str(answer)
            contributions.setdefault(agent.name, []).append(text)
            context = text
        return RunResult(context or "", contributions)

    async def panel(self, task: str, *, synthesizer: Agent | None = None) -> RunResult:
        members = [agent for agent in self.agents if agent is not synthesizer]
        answers = await asyncio.gather(
            *(agent.run(task, client=self.client, on_event=self.on_event) for agent in members)
        )
        contributions = {
            agent.name: [str(answer)] for agent, answer in zip(members, answers, strict=True)
        }
        digest = self._transcript(contributions)
        if synthesizer is None:
            return RunResult(digest, contributions)
        final = await synthesizer.run(
            "Synthesize the strongest answer to the original task. "
            "Resolve disagreements explicitly.\n\n"
            f"Original task: {task}",
            context=digest,
            client=self.client,
            on_event=self.on_event,
        )
        contributions.setdefault(synthesizer.name, []).append(str(final))
        return RunResult(str(final), contributions)

    async def debate(self, task: str, *, rounds: int = 2, judge: Agent | None = None) -> RunResult:
        if rounds < 1:
            raise ValueError("rounds must be at least 1")
        contributions: dict[str, list[str]] = {agent.name: [] for agent in self.agents}
        transcript = ""
        for round_number in range(1, rounds + 1):
            answers = await asyncio.gather(
                *(
                    agent.run(
                        f"Debate round {round_number}. Address the task and critically "
                        "improve on the discussion.",
                        context=f"Original task: {task}\n\nDebate so far:\n{transcript}"
                        if transcript
                        else task,
                        client=self.client,
                        on_event=self.on_event,
                    )
                    for agent in self.agents
                    if agent is not judge
                )
            )
            debaters = [agent for agent in self.agents if agent is not judge]
            for agent, answer in zip(debaters, answers, strict=True):
                contributions[agent.name].append(str(answer))
            transcript = self._transcript(contributions)
        if judge is None:
            return RunResult(transcript, contributions)
        verdict = await judge.run(
            f"Judge the debate and produce the final answer to: {task}",
            context=transcript,
            client=self.client,
            on_event=self.on_event,
        )
        contributions[judge.name].append(str(verdict))
        return RunResult(str(verdict), contributions)

    async def route(
        self, task: str, *, router: Agent, candidates: Sequence[Agent] | None = None
    ) -> RunResult:
        choices = list(candidates or [agent for agent in self.agents if agent is not router])
        if not choices:
            raise ValueError("Routing requires at least one candidate")
        roster = "\n".join(f"- {agent.name}: {agent.role}" for agent in choices)
        selection = await router.run(
            "Choose exactly one agent name for this task. Reply only with the name.\n\n"
            f"{roster}\n\nTask: {task}",
            client=self.client,
            on_event=self.on_event,
        )
        selected_name = str(selection).strip()
        selected = next((agent for agent in choices if agent.name == selected_name), None)
        if selected is None:
            raise ValueError(f"Router selected unknown agent: {selected_name!r}")
        answer = await selected.run(task, client=self.client, on_event=self.on_event)
        return RunResult(str(answer), {router.name: [selected_name], selected.name: [str(answer)]})

    @staticmethod
    def _transcript(contributions: dict[str, list[str]]) -> str:
        return "\n\n".join(
            f"## {name}\n" + "\n\n".join(outputs)
            for name, outputs in contributions.items()
            if outputs
        )
