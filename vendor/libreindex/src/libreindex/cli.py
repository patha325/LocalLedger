"""A compact CLI for indexing and asking one-off questions."""

from __future__ import annotations

import argparse

from .core import LibreIndex


def main() -> None:
    parser = argparse.ArgumentParser(prog="libreindex")
    parser.add_argument("folder", help="Folder containing documents")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--embedding-model", default="embeddinggemma")
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("index", help="Create or replace the local index")
    ask = actions.add_parser("ask", help="Ask a question using the existing index")
    ask.add_argument("question")
    args = parser.parse_args()
    knowledge = LibreIndex(
        args.folder, model=args.model, embedding_model=args.embedding_model
    )
    if args.action == "index":
        knowledge.index()
        print(knowledge.report.model_dump_json(indent=2))
        return
    answer = knowledge.ask(args.question)
    print(answer.text)
    if answer.warning:
        print(f"\nWarning: {answer.warning}")
    print("\nSources:")
    for citation in answer.citations:
        print(f"[{citation.number}] {citation.location} ({citation.score:.0%})")


if __name__ == "__main__":
    main()

