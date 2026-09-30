"""A full T1 + T2 run writes the report and the confusion plot."""

from pathlib import Path

from bharat_pii.config import load_bench_config
from bharat_pii.harness import run_baseline


def test_full_t1_and_t2_run_writes_report_and_plots(tmp_path: Path) -> None:
    paths = run_baseline(load_bench_config(), out_root=tmp_path)
    report = (paths.directory / "report.md").read_text(encoding="utf-8")
    assert "macro-F1" in report
    assert "Name sensitivity" in report
    assert (paths.directory / "metrics.csv").is_file()
    assert (paths.directory / "run.json").is_file()
    plots = list((paths.directory / "plots").glob("*.png"))
    assert plots
