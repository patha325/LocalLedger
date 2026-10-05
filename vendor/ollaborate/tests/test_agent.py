from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from ollaborate import Agent


class FakeMessage:
    def __init__(self, content: str, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []

    def model_dump(self, **kwargs):
        return {"role": "assistant", "content": self.content}


class FakeClient:
    def __init__(self, messages):
        self.messages = iter(messages)

    async def chat(self, **kwargs):
        return SimpleNamespace(message=next(self.messages))


@pytest.mark.asyncio
async def test_plain_response():
    result = await Agent("Ada", "researcher").run("hello", client=FakeClient([FakeMessage("hi")]))
    assert result == "hi"


@pytest.mark.asyncio
async def test_structured_response():
    class Answer(BaseModel):
        value: int

    result = await Agent("Ada", "researcher").run(
        "answer", output_type=Answer, client=FakeClient([FakeMessage('{"value": 42}')])
    )
    assert result.value == 42


@pytest.mark.asyncio
async def test_tool_loop():
    def add(a: int, b: int) -> int:
        return a + b

    call = SimpleNamespace(function=SimpleNamespace(name="add", arguments={"a": 2, "b": 3}))
    client = FakeClient([FakeMessage("", [call]), FakeMessage("5")])
    assert await Agent("Ada", "calculator", tools=[add]).run("2+3", client=client) == "5"
