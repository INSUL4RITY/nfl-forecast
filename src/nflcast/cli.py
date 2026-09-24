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
    sub.add_parser("locked-test", help="One-time evaluation including the locked test season (after decisions are frozen)")
    sub.add_parser("predict", help="Generate an immutable forecast release for the next week's unplayed games")
    sub.add_parser("score", help="Score frozen prospective releases against final results")
    sub.add_parser("export-web", help="Export versioned JSON for the website")
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
    elif args.cmd == "score":
        from nflcast.predict.score import score
        score()
    elif args.cmd == "export-web":
        from nflcast.predict.export_web import export
        export()
    elif args.cmd == "locked-test":
        from nflcast.pipeline import backtest
        backtest(include_locked=True)
    elif args.cmd == "tune":
        from nflcast.evaluation import tuning
        tuning.run()
    elif args.cmd == "predict":
        from nflcast.predict.release import generate
        generate()
    elif args.cmd == "all":
        from nflcast import pipeline
        pipeline.ingest()
        pipeline.build()
        pipeline.backtest()
        from nflcast.predict.release import generate
        generate()


if __name__ == "__main__":
    main()
