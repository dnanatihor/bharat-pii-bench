"""Command line for dataset generation. Later phases add ``run``, ``report``, and ``readme``."""

import argparse
from pathlib import Path

from bharat_pii.config import load_bench_config
from bharat_pii.dataset import build_t1, build_t2, with_seed
from bharat_pii.parquet_store import write_parquet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bpb")
    subcommands = parser.add_subparsers(dest="command", required=True)
    generate = subcommands.add_parser("generate", help="write a synthetic T1 or T2 dataset")
    generate.add_argument("--task", choices=("t1", "t2"), required=True)
    generate.add_argument("--seed", type=int)
    generate.add_argument("--out", type=Path, default=Path("data/generated"))
    args = parser.parse_args(argv)
    if args.command != "generate":
        parser.error(f"unknown command {args.command}")
    config = load_bench_config()
    if args.seed is not None:
        config = with_seed(config, args.seed)
    out = Path(args.out)
    if args.task == "t1":
        write_parquet(build_t1(config), out / "t1.parquet")
    else:
        write_parquet(build_t2(config), out / "t2.parquet")
    return 0
