"""Command-line entry point: python -m nflcast <command>."""

from __future__ import annotations

import argparse

from nflcast.config import ensure_dirs


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="nflcast")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit", help="Milestone 1 data availability audit")
    a.add_argument("--quick", action="store_true")
    sub.add_parser("ingest", help="Download/refresh raw snapshots needed by the pipeline")
    sub.add_parser("build", help="Build games table and as-of feature snapshots")
    sub.add_parser("backtest", help="Walk-forward evaluation of benchmark models")
    sub.add_parser("tune", help="Tune feature window settings on tune folds only")
    pr = sub.add_parser("predict", help="Generate a forecast release for upcoming games")
    pr.add_argument("--horizon", default="final", choices=["early", "final"])
    sub.add_parser("all", help="ingest + build + backtest + predict")
    args = p.parse_args(argv)
    ensure_dirs()

    if args.cmd == "audit":
        from nflcast.data import audit
        audit.run(quick=args.quick)
    elif args.cmd == "ingest":
        from nflcast.pipeline import ingest
        ingest()
    elif args.cmd == "build":
        from nflcast.pipeline import build
        build()
    elif args.cmd == "backtest":
        from nflcast.pipeline import backtest
        backtest()
    elif args.cmd == "tune":
        from nflcast.evaluation import tuning
        tuning.run()
    elif args.cmd == "predict":
        from nflcast.pipeline import predict
        predict(horizon=args.horizon)
    elif args.cmd == "all":
        from nflcast import pipeline
        pipeline.ingest()
        pipeline.build()
        pipeline.backtest()
        pipeline.predict(horizon="early")
        pipeline.predict(horizon="final")


if __name__ == "__main__":
    main()
