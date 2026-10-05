import json

from libreindex.readers import discover, read


def test_reads_text_csv_and_json(tmp_path) -> None:
    (tmp_path / "note.md").write_text("Local facts", encoding="utf-8")
    (tmp_path / "data.csv").write_text("name,value\nalpha,3\n", encoding="utf-8")
    (tmp_path / "data.json").write_text(json.dumps([{"city": "Stockholm"}]), encoding="utf-8")
    files = discover(tmp_path, tmp_path / ".libreindex")
    assert [path.name for path in files] == ["data.csv", "data.json", "note.md"]
    assert "name: alpha" in read(files[0], tmp_path)[0].text
    assert "Stockholm" in read(files[1], tmp_path)[0].text

