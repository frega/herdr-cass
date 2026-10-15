import json
import shutil
import subprocess
import unittest

from herdr_cass import cass

SAMPLE = {
    "hits": [
        {"source_path": "/a.jsonl", "agent": "claude_code", "workspace": "/w/a", "title": "T1",
         "snippet": "x **hit** y", "content": "full\n  message  text", "created_at": 1, "line_number": 3, "source_id": "local"},
        {"source_path": "/a.jsonl", "agent": "claude_code", "workspace": "/w/a", "title": "T1-dup"},
        {"source_path": "/b.jsonl", "agent": "codex", "workspace": None, "title": None, "snippet": None},
        {"title": "no path"},
    ]
}


class ParseHits(unittest.TestCase):
    def test_dedupes_per_session_and_strips_markup(self):
        rows = cass.parse_hits(SAMPLE)
        self.assertEqual([r["source_path"] for r in rows], ["/a.jsonl", "/b.jsonl"])
        self.assertEqual(rows[0]["title"], "T1")
        self.assertEqual(rows[0]["snippet"], "x hit y")
        self.assertEqual(rows[0]["content"], "full message text")
        self.assertEqual(rows[1]["workspace"], "")
        self.assertEqual(rows[1]["content"], "")

    @unittest.skipUnless(shutil.which("cass"), "cass not installed")
    def test_real_cass_output(self):
        out = subprocess.run(["cass", "search", "the", "--json", "--limit", "5"],
                             capture_output=True, text=True, stdin=subprocess.DEVNULL)
        if out.returncode == 0:
            for row in cass.parse_hits(json.loads(out.stdout)):
                self.assertTrue(row["source_path"])


class DirMissing(unittest.TestCase):
    def test_flags_missing_or_empty_workspace(self):
        from herdr_cass import picker
        self.assertTrue(picker.dir_missing({"workspace": "/nonexistent/xyz"}))
        self.assertTrue(picker.dir_missing({"workspace": ""}))
        self.assertFalse(picker.dir_missing({"workspace": "/tmp"}))


if __name__ == "__main__":
    unittest.main()
