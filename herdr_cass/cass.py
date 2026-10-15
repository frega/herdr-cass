"""Thin wrapper around the cass CLI. Never runs bare `cass` (it starts a blocking TUI)."""

import json
import shutil
import subprocess


class CassError(Exception):
    pass


def _run(args, timeout=60):
    if not shutil.which("cass"):
        raise CassError("cass not found on PATH (https://github.com/Dicklesworthstone/coding_agent_session_search)")
    try:
        proc = subprocess.run(["cass", *args], capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise CassError(f"cass {args[0]} timed out") from None
    return proc


def health():
    """None when cass is usable, else a short problem description."""
    try:
        proc = _run(["health"], timeout=10)
    except CassError as err:
        return str(err)
    if proc.returncode != 0:
        return "cass index is not healthy; run `cass index` (or `cass doctor`)"
    return None


def parse_hits(payload):
    """One row per session (source_path), best-scored hit first; payload is `cass search --json` output."""
    sessions = {}
    for hit in payload.get("hits", []):
        path = hit.get("source_path")
        if not path or path in sessions:
            continue
        sessions[path] = {
            "source_path": path,
            "agent": hit.get("agent") or "?",
            "workspace": hit.get("workspace") or "",
            "title": hit.get("title") or "",
            "snippet": (hit.get("snippet") or "").replace("**", ""),
            "content": " ".join((hit.get("content") or "").split())[:1500],
            "created_at": hit.get("created_at"),
            "line_number": hit.get("line_number"),
            "source_id": hit.get("source_id"),
        }
    return list(sessions.values())


def search(query, limit=50):
    # Over-fetch: several hits usually belong to the same session.
    proc = _run(["search", query, "--json", "--limit", str(limit * 3)])
    if proc.returncode != 0:
        lines = (proc.stderr or proc.stdout).strip().splitlines()
        raise CassError(lines[-1] if lines else "cass search failed")
    try:
        return parse_hits(json.loads(proc.stdout))[:limit]
    except ValueError:
        raise CassError("cass search returned invalid JSON") from None


def resume_command(source_path):
    """Shell-ready resume command line, as cass resolves it for the session's native harness."""
    proc = _run(["resume", source_path, "--shell"], timeout=15)
    out = proc.stdout.strip()
    if proc.returncode != 0 or not out:
        detail = proc.stderr.strip().splitlines()[-1:] or ["cass could not resolve a resume command"]
        raise CassError(detail[0])
    return out
