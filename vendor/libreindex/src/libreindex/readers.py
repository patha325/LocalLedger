"""Small, dependency-light readers for LibreIndex's supported formats."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pypdf import PdfReader

SUPPORTED_SUFFIXES = {".pdf", ".md", ".markdown", ".txt", ".csv", ".json"}


@dataclass(frozen=True)
class Document:
    text: str
    path: str
    page: int | None = None
    record: int | None = None


def discover(root: Path, database_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if database_dir == path or database_dir in path.parents:
            continue
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
            files.append(path)
    return sorted(files)


def read(path: Path, root: Path) -> list[Document]:
    suffix = path.suffix.lower()
    relative = path.relative_to(root).as_posix()
    if suffix == ".pdf":
        return _read_pdf(path, relative)
    if suffix == ".csv":
        return _read_csv(path, relative)
    if suffix == ".json":
        return _read_json(path, relative)
    text = path.read_text(encoding="utf-8", errors="replace")
    return [Document(text=text, path=relative)] if text.strip() else []


def _read_pdf(path: Path, relative: str) -> list[Document]:
    result = []
    for number, page in enumerate(PdfReader(path).pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            result.append(Document(text=text, path=relative, page=number))
    return result


def _read_csv(path: Path, relative: str) -> list[Document]:
    result = []
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=1):
            text = "\n".join(f"{key}: {value}" for key, value in row.items())
            if text.strip():
                result.append(Document(text=text, path=relative, record=number))
    return result


def _read_json(path: Path, relative: str) -> list[Document]:
    value = json.loads(path.read_text(encoding="utf-8"))
    records: Iterable[Any] = value if isinstance(value, list) else [value]
    return [
        Document(
            text=json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
            path=relative,
            record=number,
        )
        for number, record in enumerate(records, start=1)
    ]

