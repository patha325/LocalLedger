import asyncio

from ollaborate import Agent, Team


async def main() -> None:
    researcher = Agent("Curie", "evidence-focused researcher", model="qwen3:8b")
    skeptic = Agent("Feynman", "skeptical reviewer", model="qwen3:8b")
    editor = Agent("Sagan", "clear technical editor", model="qwen3:8b")

    result = await Team(researcher, skeptic, editor).panel(
        "Explain whether a Mars settlement can make its own rocket propellant.",
        synthesizer=editor,
    )
    print(result.output)


if __name__ == "__main__":
    asyncio.run(main())
