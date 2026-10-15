import argparse
import json
import os
import sys

from . import cass
from .herdr import Client, HerdrError

PLUGIN_ID = "frega.cass"


def context():
    try:
        return json.loads(os.environ.get("HERDR_PLUGIN_CONTEXT_JSON") or "{}")
    except ValueError:
        return {}


def cmd_open_search(args, client):
    # The popup has no workspace of its own, so hand it the one the key was pressed in.
    ctx = context()
    env = {"HERDR_CASS_WORKSPACE_ID": ctx.get("workspace_id") or os.environ.get("HERDR_WORKSPACE_ID") or ""}
    client.plugin_pane_open(os.environ.get("HERDR_PLUGIN_ID", PLUGIN_ID), "search", env=env)


def cmd_search(args, client):
    from .picker import run

    run(os.environ.get("HERDR_CASS_WORKSPACE_ID") or os.environ.get("HERDR_WORKSPACE_ID"))


def cmd_query(args, client):
    """Non-interactive: print the matching sessions (handy for checking cass integration)."""
    problem = cass.health()
    if problem:
        raise cass.CassError(problem)
    hits = cass.search(args.query, limit=args.limit)
    if args.json:
        print(json.dumps(hits, indent=2))
        return
    for h in hits:
        print(f"{h['agent']:12} {h['workspace']}  {h['title'][:60]}")


def main(argv):
    parser = argparse.ArgumentParser(prog="herdr-cass")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("open-search").set_defaults(fn=cmd_open_search)
    sub.add_parser("search", help="search popup (curses)").set_defaults(fn=cmd_search)
    p = sub.add_parser("query", help="print matching sessions without the UI")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_query)

    args = parser.parse_args(argv)
    client = Client()
    try:
        args.fn(args, client)
    except (cass.CassError, HerdrError, OSError) as err:
        client.notify("Cass", str(err))
        print(f"herdr-cass: {err}", file=sys.stderr)
        return 1
    return 0
