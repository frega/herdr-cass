# herdr-cass

Search all your coding-agent sessions with [cass](https://github.com/Dicklesworthstone/coding_agent_session_search)
from inside herdr, and resume a hit in a new tab.

- **Search popup:** type a query, enter to search; results are one row per session
  (age, agent, project, title). Arrow keys or `tab` move into the list; enter opens a
  new tab in the current workspace, in the session's project directory, and types the
  resume command into its shell.
- The resume command comes from `cass resume`, so every harness cass supports
  (Claude Code, Codex, OpenCode, Pi, Gemini, ...) resumes the way cass resolves it.
- Without cass, or with an unhealthy index, the popup says so (`cass index` fixes a stale index).

Requires herdr ≥ 0.8, `python3` (stdlib only) and `cass` on the PATH.

**Privacy:** cass builds a full-text index of every local agent transcript. That is
opt-in on your side (you install and run `cass index`); this plugin only queries it.

## Install

```bash
herdr plugin install frega/herdr-cass
# or, from a local checkout:
herdr plugin link /path/to/herdr-cass
```

Bind a key in `~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "prefix+/"
type = "plugin_action"
command = "frega.cass.search"
description = "search agent sessions"
```

`bin/herdr-cass query "<text>"` prints matches without the UI.

## Development

`task check` compiles, validates the manifest and runs the tests; `task link` links the checkout.
