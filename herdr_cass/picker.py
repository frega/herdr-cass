"""Popup: type a query, Enter to search, pick a session, Enter to resume it in a new tab."""

import curses
import os
import textwrap
import time

from . import cass
from .herdr import Client, HerdrError


PREVIEW_LINES = 4  # rows of the matched message shown under the list


def age(ms):
    if not ms:
        return "?"
    secs = max(0, time.time() - ms / 1000)
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{int(secs // size)}{unit}"
    return "now"


def open_in_new_tab(client, workspace_id, hit):
    """New tab at the hit's project directory, with cass's resume command typed into its shell."""
    command = cass.resume_command(hit["source_path"])
    cwd = hit["workspace"] if os.path.isdir(hit["workspace"] or "") else os.path.expanduser("~")
    label = (hit["title"] or hit["agent"])[:30]
    created = client.tab_create(workspace_id, cwd, label)
    # Typed into the shell rather than spawned as the pane process, so the pane
    # survives the agent exiting (same as herdr-suspenders).
    client.pane_send_input(created["root_pane"]["pane_id"], command)


def dir_missing(hit):
    """True when the session's project directory isn't on this machine (resume would start in ~)."""
    return not os.path.isdir(hit["workspace"])


class Picker:
    def __init__(self, workspace_id):
        self.client = Client()
        self.workspace_id = workspace_id
        self.query = ""
        self.hits = []
        self.index = 0
        self.message = ""
        self.problem = cass.health()
        if self.problem and "not found" not in self.problem:
            self.problem += " — you can still try searching"

    def draw(self, scr):
        scr.erase()
        h, w = scr.getmaxyx()
        scr.addnstr(0, 0, f" Search sessions: {self.query}", w - 1, curses.A_BOLD)
        rows = max(1, h - PREVIEW_LINES - 4)
        top = max(0, self.index - rows + 1)
        for row, hit in enumerate(self.hits[top : top + rows]):
            i = top + row
            ws = os.path.basename(hit["workspace"].rstrip("/")) or "-"
            flag = "!" if dir_missing(hit) else " "
            line = f" {flag} {age(hit['created_at']):>4}  {hit['agent']:12} {ws:22} {hit['title'] or hit['snippet']}"
            scr.addnstr(1 + row, 0, line.ljust(w - 1), w - 1, curses.A_REVERSE if i == self.index else 0)
        if not self.hits:
            scr.addnstr(2, 2, "Type a query and press enter." if not self.message else "No sessions.", w - 3)

        y = h - PREVIEW_LINES - 3
        scr.hline(y, 0, curses.ACS_HLINE, w)
        if self.hits:
            hit = self.hits[self.index]
            gone = "  [directory missing: resume starts in ~ and may not find the session]" if dir_missing(hit) else ""
            scr.addnstr(y + 1, 1, (hit["workspace"] or "(no project)") + gone, w - 2)
            text = hit["content"] or hit["snippet"]
            for n, line in enumerate(textwrap.wrap(text, max(10, w - 2))[:PREVIEW_LINES]):
                scr.addnstr(y + 2 + n, 1, line, w - 2, curses.A_DIM)
        status = self.message or self.problem or "! project dir missing · enter search / resume selected · ↑↓ move · tab focus list/query · esc close"
        scr.addnstr(h - 1, 0, f" {status}", w - 1, curses.A_BOLD if (self.message or self.problem) else curses.A_DIM)
        scr.refresh()

    def do_search(self):
        self.message = ""
        try:
            self.hits = cass.search(self.query)
            self.index = 0
            if not self.hits:
                self.message = "No sessions."
        except cass.CassError as err:
            self.hits, self.message = [], str(err)

    def run(self, scr):
        curses.set_escdelay(25)
        curses.curs_set(0)
        scr.keypad(True)
        browsing = False  # enter searches while typing, resumes while browsing results
        while True:
            self.draw(scr)
            key = scr.get_wch()
            self.message = ""
            if key == "\x1b":
                return
            if key in (curses.KEY_UP, "\x10"):
                self.index = max(0, self.index - 1)
                browsing = bool(self.hits)
            elif key in (curses.KEY_DOWN, "\x0e"):
                self.index = min(max(0, len(self.hits) - 1), self.index + 1)
                browsing = bool(self.hits)
            elif key == "\t":
                browsing = bool(self.hits) and not browsing
            elif key in ("\n", "\r", curses.KEY_ENTER):
                if browsing and self.hits:
                    try:
                        open_in_new_tab(self.client, self.workspace_id, self.hits[self.index])
                        return
                    except (cass.CassError, HerdrError, OSError) as err:
                        self.message = f"resume failed: {err}"
                elif self.query.strip():
                    self.draw_busy(scr)
                    self.do_search()
                    browsing = bool(self.hits)
            elif key in (curses.KEY_BACKSPACE, "\x7f"):
                self.query, browsing = self.query[:-1], False
            elif isinstance(key, str) and key.isprintable():
                self.query, browsing = self.query + key, False

    def draw_busy(self, scr):
        h, w = scr.getmaxyx()
        scr.move(h - 1, 0)
        scr.clrtoeol()
        scr.addnstr(h - 1, 0, " Searching…", w - 1, curses.A_BOLD)
        scr.refresh()


def run(workspace_id):
    curses.wrapper(Picker(workspace_id).run)
