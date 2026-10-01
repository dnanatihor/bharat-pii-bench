"""Command line for dataset generation. Later phases add ``run``, ``report``, and ``readme``."""

import argparse
from pathlib import Path

from bharat_pii.config import load_bench_config
from bharat_pii.dataset import build_t1, build_t2, with_seed
from bharat_pii.harness import default_config, run_baseline
from bharat_pii.parquet_store import write_parquet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bpb")
    subcommands = parser.add_subparsers(dest="command", required=True)
    generate = subcommands.add_parser("generate", help="write a synthetic T1 or T2 dataset")
    generate.add_argument("--task", choices=("t1", "t2"), required=True)
    generate.add_argument("--seed", type=int)
    generate.add_argument("--out", type=Path, default=Path("data/generated"))
    run = subcommands.add_parser("run", help="score detectors and write a report")
    run.add_argument("--detectors", default="regex_checksum")
    run.add_argument("--task", choices=("t1", "t2", "both"), default="both")
    run.add_argument("--split", choices=("dev", "test"), default="test")
    run.add_argument("--seed", type=int)
    run.add_argument("--out", type=Path, default=Path("results"))
    run.add_argument("--budget-usd", type=float)
    report = subcommands.add_parser("report", help="print a saved report")
    report.add_argument("run_dir", type=Path)
    args = parser.parse_args(argv)
    if args.command == "generate":
        return _generate(args.task, args.seed, Path(args.out))
    if args.command == "run":
        config = default_config(args.seed)
        detectors = tuple(part.strip() for part in str(args.detectors).split(",") if part.strip())
        tasks = ("t1", "t2") if args.task == "both" else (str(args.task),)
        paths = run_baseline(
            config,
            detectors=detectors,
            tasks=tasks,
            split=str(args.split),
            out_root=Path(args.out),
            budget_usd=args.budget_usd,
        )
        print(paths.directory)
        return 0
    if args.command == "report":
        text = (Path(args.run_dir) / "report.md").read_text(encoding="utf-8")
        print(text, end="")
        return 0
    parser.error(f"unknown command {args.command}")
    return 2


def _generate(task: str, seed: int | None, out: Path) -> int:
    config = load_bench_config()
    if seed is not None:
        config = with_seed(config, seed)
    if task == "t1":
        write_parquet(build_t1(config), out / "t1.parquet")
    else:
        write_parquet(build_t2(config), out / "t2.parquet")
    return 0
