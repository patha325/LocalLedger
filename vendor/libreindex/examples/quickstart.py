from libreindex import LibreIndex

knowledge = LibreIndex("./documents").index()
answer = knowledge.ask("What are the main conclusions?")

print(answer.text)
for source in answer.citations:
    print(source.location, source.score, source.excerpt)

