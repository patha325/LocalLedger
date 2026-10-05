import pytest

from libreindex.chunking import chunks


def test_chunks_short_text() -> None:
    assert chunks("a short document", size=50, overlap=5) == ["a short document"]


def test_chunks_overlap() -> None:
    result = chunks("0123456789" * 4, size=20, overlap=5)
    assert len(result) == 3
    assert result[0][-5:] == result[1][:5]


def test_chunks_rejects_invalid_settings() -> None:
    with pytest.raises(ValueError):
        chunks("text", size=10, overlap=10)

