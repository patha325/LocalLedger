"""The public LibreIndex API."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import lancedb

from .backend import Backend, OllamaBackend
from .chunking import chunks
from .models import Answer, Citation, IndexReport
from .readers import discover, read


class LibreIndex:
    """Index a folder and answer questions using only local Ollama models."""

    def __init__(
        self,
        folder: str | Path,
        *,
        model: str = "qwen3:8b",
        embedding_model: str = "embeddinggemma",
        database: str | Path | None = None,
        host: str = "http://127.0.0.1:11434",
        chunk_size: int = 1_200,
        chunk_overlap: int = 200,
        top_k: int = 5,
        confidence_threshold: float = 0.45,
        backend: Backend | None = None,
    ) -> None:
        self.folder = Path(folder).expanduser().resolve()
        if not self.folder.is_dir():
            raise NotADirectoryError(f"Document folder does not exist: {self.folder}")
        self.database = (
            Path(database).expanduser().resolve()
            if database is not None
            else self.folder / ".libreindex"
        )
        self.model = model
        self.embedding_model = embedding_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.top_k = top_k
        self.confidence_threshold = confidence_threshold
        self.backend = backend or OllamaBackend(host)

    def index(self) -> LibreIndex:
        """Index all supported files and return ``self`` for fluent use."""
        files = discover(self.folder, self.database)
        rows: list[dict[str, object]] = []
        document_count = 0
        skipped = 0
        for path in files:
            try:
                documents = read(path, self.folder)
            except (OSError, ValueError):
                skipped += 1
                continue
            document_count += len(documents)
            for document in documents:
                for position, text in enumerate(
                    chunks(document.text, self.chunk_size, self.chunk_overlap)
                ):
                    identity = f"{document.path}:{document.page}:{document.record}:{position}"
                    rows.append(
                        {
                            "id": hashlib.sha256(identity.encode()).hexdigest(),
                            "text": text,
                            "path": document.path,
                            "page": document.page or -1,
                            "record": document.record or -1,
                            "position": position,
                        }
                    )
        if not rows:
            raise ValueError("No readable content found in supported files")
        vectors = self.backend.embed([str(row["text"]) for row in rows], self.embedding_model)
        if len(vectors) != len(rows):
            raise RuntimeError("Embedding backend returned an unexpected number of vectors")
        for row, vector in zip(rows, vectors, strict=True):
            row["vector"] = vector
        if self.database.exists():
            shutil.rmtree(self.database)
        self.database.mkdir(parents=True, exist_ok=True)
        database = lancedb.connect(self.database)
        database.create_table("chunks", data=rows, mode="overwrite")
        self._last_report = IndexReport(
            files=len(files),
            documents=document_count,
            chunks=len(rows),
            skipped=skipped,
            database=str(self.database),
        )
        return self

    @property
    def report(self) -> IndexReport:
        """Return the report from the most recent indexing run."""
        if not hasattr(self, "_last_report"):
            raise RuntimeError("No indexing run has completed")
        return self._last_report

    def ask(self, question: str, *, top_k: int | None = None) -> Answer:
        """Answer a question and return citations, excerpts, and confidence."""
        if not question.strip():
            raise ValueError("question cannot be empty")
        if not self.database.exists():
            raise RuntimeError("No index found. Call .index() first.")
        database = lancedb.connect(self.database)
        if "chunks" not in database.list_tables().tables:
            raise RuntimeError("No index found. Call .index() first.")
        vector = self.backend.embed([question], self.embedding_model)[0]
        limit = top_k or self.top_k
        records = (
            database.open_table("chunks")
            .search(vector)
            .distance_type("cosine")
            .limit(limit)
            .to_list()
        )
        citations = tuple(self._citation(number, row) for number, row in enumerate(records, 1))
        confidence = citations[0].score if citations else 0.0
        warning = None
        if confidence < self.confidence_threshold:
            warning = (
                "The indexed files provide weak support for this answer "
                f"(retrieval confidence {confidence:.0%})."
            )
        context = "\n\n".join(
            f"SOURCE [{item.number}] {item.location}\n{item.excerpt}" for item in citations
        )
        prompt = f"""You answer questions using only the supplied sources.
If the sources are incomplete, say so explicitly. Do not use outside knowledge.
Cite factual claims using source markers such as [1] or [2].

QUESTION:
{question}

SOURCES:
{context}

ANSWER:"""
        text = self.backend.generate(prompt, self.model)
        return Answer(text=text, citations=citations, confidence=confidence, warning=warning)

    @staticmethod
    def _citation(number: int, row: dict[str, object]) -> Citation:
        distance = float(row.get("_distance", 1.0))
        score = max(0.0, min(1.0, 1.0 - distance))
        return Citation(
            number=number,
            path=str(row["path"]),
            excerpt=str(row["text"]),
            score=score,
            page=None if int(row["page"]) < 0 else int(row["page"]),
            record=None if int(row["record"]) < 0 else int(row["record"]),
        )
