from collections.abc import Sequence

from libreindex import LibreIndex


class FakeBackend:
    def embed(self, texts: Sequence[str], model: str) -> list[list[float]]:
        return [[1.0, 0.0] if "mars" in text.lower() else [0.8, 0.2] for text in texts]

    def generate(self, prompt: str, model: str) -> str:
        assert "SOURCE [1]" in prompt
        return "The launch is scheduled for 2031 [1]."


def test_index_and_ask(tmp_path) -> None:
    (tmp_path / "mission.txt").write_text(
        "The Mars mission launch is scheduled for 2031.", encoding="utf-8"
    )
    index = LibreIndex(tmp_path, backend=FakeBackend()).index()
    answer = index.ask("When is the Mars launch?")
    assert answer.text.endswith("[1].")
    assert answer.citations[0].path == "mission.txt"
    assert index.report.files == 1

