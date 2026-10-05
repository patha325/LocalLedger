# LibreIndex

**Local files. Local models. Answers with evidence.**

LibreIndex is a small Python library that connects a folder of files to local
Ollama models. It indexes PDF, Markdown, text, CSV, and JSON into an embedded
LanceDB database, then answers questions with citations and source excerpts.

Nothing is uploaded. The default Ollama endpoint is `127.0.0.1`, and the index
is stored inside the document folder.

## Why LibreIndex?

RAG frameworks are often much larger than the problem they solve. LibreIndex
offers one opinionated path from a folder to grounded answers:

- three-line Python API;
- fully local generation and embeddings through Ollama;
- persistent embedded vector search;
- inspectable citations, excerpts, and retrieval confidence;
- explicit re-indexing when files change;
- no orchestration-framework lock-in.

LibreIndex is designed as a focused companion to
[Ollaborate](https://github.com/patha325/ollaborate): LibreIndex supplies local
knowledge; Ollaborate supplies local multi-agent orchestration.

## Install

Install Ollama, then pull the default models:

```bash
ollama pull qwen3:8b
ollama pull embeddinggemma
pip install libreindex
```

## Three-line quick start

```python
from libreindex import LibreIndex
knowledge = LibreIndex("./documents").index()
answer = knowledge.ask("What are the main conclusions?")
```

`print(answer)` prints the generated text. The structured result is also easy
to inspect:

```python
print(answer.text)
print(answer.confidence)
print(answer.warning)

for citation in answer.citations:
    print(citation.location)
    print(citation.excerpt)
```

## Re-index after changes

Indexing is intentionally explicit:

```python
knowledge.index()
```

The operation replaces the existing local index. LibreIndex never watches or
uploads the folder.

## Override the defaults

```python
knowledge = LibreIndex(
    "./documents",
    model="gemma3:12b",
    embedding_model="qwen3-embedding:0.6b",
    database="./my-index",
    top_k=8,
    confidence_threshold=0.55,
).index()
```

## Command line

```bash
libreindex ./documents index
libreindex ./documents ask "What changed between the reports?"
```

## Supported files

| Format | Extensions | Citation location |
| --- | --- | --- |
| PDF | `.pdf` | Page |
| Markdown | `.md`, `.markdown` | File |
| Text | `.txt` | File |
| CSV | `.csv` | Record |
| JSON | `.json` | Record |

Scanned PDFs require OCR before indexing. Files that cannot be read are counted
as skipped in `knowledge.report`.

## Confidence

`answer.confidence` is a retrieval score derived from the closest source chunk;
it is not a calibrated probability that the generated answer is correct. When
the score falls below the configured threshold, LibreIndex returns a warning
while still answering from the retrieved context.

## Offline boundary

LibreIndex itself makes no cloud API calls. It talks only to the configured
Ollama host. Full offline operation requires models to be downloaded in advance
and the default local host to be retained.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest
python -m build
twine check dist/*
```

## License

MIT
