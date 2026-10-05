"""Public value objects returned by LibreIndex."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Citation(BaseModel):
    """A retrieved source excerpt supporting an answer."""

    model_config = ConfigDict(frozen=True)

    number: int
    path: str
    excerpt: str
    score: float = Field(ge=0.0, le=1.0)
    page: int | None = None
    record: int | None = None

    @property
    def location(self) -> str:
        suffix = f" (page {self.page})" if self.page is not None else ""
        suffix = f" (record {self.record})" if self.record is not None else suffix
        return f"{self.path}{suffix}"


class Answer(BaseModel):
    """A generated answer with inspectable evidence."""

    model_config = ConfigDict(frozen=True)

    text: str
    citations: tuple[Citation, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)
    warning: str | None = None

    def __str__(self) -> str:
        return self.text


class IndexReport(BaseModel):
    """Summary of a completed indexing run."""

    model_config = ConfigDict(frozen=True)

    files: int
    documents: int
    chunks: int
    skipped: int
    database: str

