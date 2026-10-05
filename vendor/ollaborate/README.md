# Ollaborate

**Multi-agent orchestration for Ollama, without the framework tax.**

Ollaborate gives local models a clean team API: define specialists, choose a proven collaboration pattern, and run. No cloud keys, YAML maze, graph DSL, or hidden global state.

```bash
pip install ollaborate
ollama pull qwen3:8b
```

```python
import asyncio
from ollaborate import Agent, Team


async def main():
    researcher = Agent("Curie", "evidence-focused researcher")
    skeptic = Agent("Feynman", "skeptical reviewer")
    editor = Agent("Sagan", "clear technical editor")

    result = await Team(researcher, skeptic, editor).panel(
        "Can a Mars settlement manufacture its own rocket propellant?",
        synthesizer=editor,
    )
    print(result.output)


asyncio.run(main())
```

## Why Ollaborate?

- **Small API:** `Agent` and `Team` are enough to begin.
- **Useful patterns:** concurrent panels, sequential pipelines, bounded debates, and supervisor routing.
- **Native Ollama:** tools and JSON-schema structured outputs use Ollama directly.
- **Inspectable:** every contribution is returned; lifecycle events support logging and UIs.
- **Safe by construction:** tool loops and debates are bounded.
- **Hackable:** ordinary Python, callable tools, and dependency injection for testing.

## Patterns

```python
await team.pipeline(task)  # A → B → C
await team.panel(task, synthesizer=editor)  # A + B → editor
await team.debate(task, rounds=2, judge=editor)  # bounded critique → verdict
await team.route(task, router=dispatcher)  # choose one specialist
```

Every run returns a `RunResult` with `.output` and `.contributions`.

## Tools

Pass ordinary typed Python functions. Ollama derives their tool schemas from signatures and docstrings.

```python
def weather(city: str) -> str:
    """Return the current weather for a city."""
    return "12 C and raining"


analyst = Agent("Analyst", "travel analyst", tools=[weather])
```

Treat model-requested tool arguments as untrusted input. Keep dangerous tools sandboxed and require human approval where appropriate.

## Structured outputs

```python
from pydantic import BaseModel


class Finding(BaseModel):
    claim: str
    confidence: float


finding = await researcher.run("Assess the claim", output_type=Finding)
```

## Observability

```python
team = Team(researcher, skeptic, on_event=lambda event: print(event.kind, event.agent))
```

Events include agent starts/ends, tool calls/results, and errors. Do not log secrets returned by tools.

## Development

```bash
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
ruff check .
pytest
python -m build
```

## Status

Ollaborate is alpha software. The public API is intentionally small, but may evolve before 1.0.

## License

MIT. Ollaborate is an independent project and is not affiliated with Ollama.

