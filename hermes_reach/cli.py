from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable

from . import __version__
from .channels import CHANNELS, CheckResult, get_channel


ORDER = {"warn": 0, "off": 1, "ok": 2}


def _icon(status: str) -> str:
    return {"ok": "✅", "warn": "⚠️", "off": "⬜"}.get(status, "❔")


def _iter_results():
    for channel in CHANNELS:
        result = channel.check()
        yield channel, result


def cmd_doctor(args: argparse.Namespace) -> int:
    rows = list(_iter_results())
    if args.json:
        print(json.dumps([
            {
                "key": ch.key,
                "title": ch.title,
                "status": res.status,
                "detail": res.detail,
                "action": res.action,
                "risk": ch.risk,
                "default_path": ch.default_path,
            }
            for ch, res in rows
        ], indent=2))
        return 0

    print(f"Hermes Reach doctor v{__version__}\n")
    for ch, res in rows:
        print(f"{_icon(res.status)} {ch.key:16} {ch.title}")
        print(f"   path: {ch.default_path}")
        print(f"   risk: {ch.risk}")
        print(f"   {res.detail}")
        if res.action:
            print(f"   action: {res.action}")
        print()
    return 0 if all(res.status == "ok" for _, res in rows) else 1


def cmd_queue(args: argparse.Namespace) -> int:
    rows = sorted(_iter_results(), key=lambda pair: (ORDER.get(pair[1].status, 99), pair[0].risk, pair[0].key))
    actionable = [(ch, res) for ch, res in rows if res.status != "ok" or args.all]
    if args.json:
        print(json.dumps([
            {
                "key": ch.key,
                "status": res.status,
                "title": ch.title,
                "why": res.detail,
                "next_action": res.action or "; ".join(ch.setup_plan),
                "risk": ch.risk,
            }
            for ch, res in actionable
        ], indent=2))
        return 0

    print("Hermes Reach queue\n")
    if not actionable:
        print("No actionable channel gaps. All checks are green.")
        return 0
    for i, (ch, res) in enumerate(actionable, start=1):
        print(f"{i}. {_icon(res.status)} {ch.title} [{ch.key}] — {res.status}, risk={ch.risk}")
        print(f"   Why: {res.detail}")
        next_action = res.action or "; ".join(ch.setup_plan)
        print(f"   Next: {next_action}")
        print()
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    try:
        ch = get_channel(args.channel)
    except KeyError:
        print(f"Unknown channel: {args.channel}", file=sys.stderr)
        print("Known channels: " + ", ".join(c.key for c in CHANNELS), file=sys.stderr)
        return 2
    res = ch.check()
    print(f"# Setup / usage plan: {ch.title} ({ch.key})\n")
    print(f"Current status: {_icon(res.status)} {res.status}")
    print(f"Current path: {ch.default_path}")
    print(f"Risk: {ch.risk}")
    print(f"Observed: {res.detail}")
    if res.action:
        print(f"Immediate action: {res.action}")
    print("\nSteps:")
    for i, step in enumerate(ch.setup_plan, start=1):
        print(f"{i}. {step}")
    if ch.risk == "high":
        print("\nGuardrail: this channel may involve cookies, credentials, paid APIs, or posting. Ask before mutating setup.")
    return 0


def cmd_capability_radar(args: argparse.Namespace) -> int:
    checks = {ch.key: res for ch, res in _iter_results()}
    print("# Hermes Capability Radar\n")
    for key in ["hermes-upstream", "docs-watcher", "newsletter", "x-search", "agent-reach"]:
        ch = get_channel(key)
        res = checks[key]
        print(f"- **{ch.title}:** {_icon(res.status)} {res.detail}")
        if res.action:
            print(f"  - Action: {res.action}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-reach", description="Hermes-native internet capability doctor and queue")
    parser.add_argument("--version", action="version", version=f"hermes-reach {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    doctor = sub.add_parser("doctor", help="Check all channel capabilities")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    queue = sub.add_parser("queue", help="Show prioritized channel/setup gaps")
    queue.add_argument("--json", action="store_true")
    queue.add_argument("--all", action="store_true", help="Include green checks too")
    queue.set_defaults(func=cmd_queue)

    plan = sub.add_parser("plan", help="Print safe setup/usage plan for one channel")
    plan.add_argument("channel")
    plan.set_defaults(func=cmd_plan)

    radar = sub.add_parser("capability-radar", help="Summarize install-vs-capability state")
    radar.set_defaults(func=cmd_capability_radar)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
