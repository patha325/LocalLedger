import pytest

from ollaborate import Agent, Team


class ScriptedAgent(Agent):
    def __init__(self, name: str, role: str, *answers: str):
        super().__init__(name, role)
        self._replies = iter(answers)

    async def run(self, task, **kwargs):
        return next(self._replies)


@pytest.mark.asyncio
async def test_pipeline():
    team = Team(ScriptedAgent("A", "first", "draft"), ScriptedAgent("B", "second", "final"))
    result = await team.pipeline("work")
    assert result.output == "final"
    assert result.contributions == {"A": ["draft"], "B": ["final"]}


@pytest.mark.asyncio
async def test_panel_with_synthesis():
    a = ScriptedAgent("A", "optimist", "yes")
    b = ScriptedAgent("B", "skeptic", "no")
    judge = ScriptedAgent("Judge", "synthesizer", "maybe")
    result = await Team(a, b, judge).panel("decide", synthesizer=judge)
    assert result.output == "maybe"


@pytest.mark.asyncio
async def test_route():
    router = ScriptedAgent("Router", "router", "Coder")
    coder = ScriptedAgent("Coder", "writes code", "print('hi')")
    result = await Team(router, coder).route("code", router=router)
    assert result.output == "print('hi')"
