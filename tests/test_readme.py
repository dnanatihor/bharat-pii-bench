"""The leaderboard is generated from metrics files, not written by hand."""

from pathlib import Path

from bharat_pii.readme import END, START, update_readme


def test_readme_leaderboard_comes_from_metrics(tmp_path: Path) -> None:
    run = tmp_path / "results" / "sample"
    run.mkdir(parents=True)
    (run / "metrics.csv").write_text(
        "\n".join(
            [
                "detector,task,label,precision,recall,f1,support",
                "regex_checksum,t1,IN_PAN,1.000000,1.000000,1.000000,2",
                "regex_checksum,t1,NONE,0.000000,0.000000,0.000000,2",
                "regex_checksum,t2,truthful,,,0.800000,1",
                "regex_checksum,t2,obfuscated,,,0.500000,1",
                "regex_checksum,t2,misleading,,,0.250000,1",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    readme = tmp_path / "README.md"
    readme.write_text(f"# Title\n\n{START}\nold\n{END}\n", encoding="utf-8")
    block = update_readme(readme, tmp_path / "results")
    text = readme.read_text(encoding="utf-8")
    assert "regex_checksum" in block
    assert "1.0000" in block
    assert "0.8000" in block
    assert "0.5000" in block
    assert "0.2500" in block
    assert "0.5500" in block
    assert "old" not in text
    assert text.index(START) < text.index("regex_checksum") < text.index(END)
    again = update_readme(readme, tmp_path / "results")
    assert again == block
