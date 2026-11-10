"""Tests for the webnovel-workflow bookkeeping tool. Run with: python3 -m unittest discover -s tests"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "webnovel-workflow" / "references" / "tools"))

import novel  # noqa: E402


class CountTest(unittest.TestCase):
    def test_counts_prose_without_whitespace_or_headings(self):
        text = "# 第一章 雨夜\n\n他推开门。\n\n　　“谁？”\n"
        self.assertEqual(novel.count_chars(text), len("他推开门。“谁？”"))

    def test_stops_at_the_notes_section(self):
        text = "正文一句。\n\n## 待确认事项\n- 新设定：某某\n"
        self.assertEqual(novel.count_chars(text), 5)

    def test_target_comparison(self):
        self.assertIn("两成以内", novel.compare_to_target(2300, 2500))
        self.assertIn("少了 40%", novel.compare_to_target(1500, 2500))
        self.assertIn("多了 30%", novel.compare_to_target(3250, 2500))
        self.assertEqual(novel.compare_to_target(2000, 0), "")


class DiffTest(unittest.TestCase):
    def test_reports_deleted_added_and_rewritten_paragraphs(self):
        old = "甲段不变。\n乙段是多余的解释。\n丙段他说了一句话。\n"
        new = "甲段不变。\n丙段他低声说了一句话。\n丁段是新加的。\n"
        changes = novel.diff_paragraphs(old, new)
        kinds = [kind for kind, _, _ in changes]
        self.assertEqual(sorted(kinds), ["删", "加", "改"])
        self.assertIn(("删", "乙段是多余的解释。", ""), changes)
        self.assertIn(("加", "", "丁段是新加的。"), changes)

    def test_identical_text_has_no_changes(self):
        self.assertEqual(novel.diff_paragraphs("一段。\n二段。", "一段。\n\n二段。\n"), [])


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name) / "书"

    def test_init_creates_the_archive_and_keeps_existing_files(self):
        self.project.mkdir()
        (self.project / "02-设定.md").write_text("作者自己的设定", encoding="utf-8")
        created, kept = novel.init_project(self.project)
        self.assertEqual(kept, ["02-设定.md"])
        self.assertIn("00-写作规则.md", created)
        self.assertIn("01-项目状态.md", created)
        self.assertNotIn("记录-资源.md", created)
        self.assertEqual((self.project / "02-设定.md").read_text(encoding="utf-8"), "作者自己的设定")
        self.assertTrue((self.project / "正文").is_dir())
        self.assertTrue((self.project / "待确认").is_dir())
        created_again, _ = novel.init_project(self.project, resources=True)
        self.assertEqual(created_again, ["记录-资源.md"])

    def _draft(self, name, text="他推开门。"):
        path = self.project / "待确认" / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_adopt_files_the_chapter_and_archives_only_its_drafts(self):
        novel.init_project(self.project)
        self._draft("第003章-处境卡.md")
        self._draft("第003章-v1-初稿.md")
        chosen = self._draft("第003章-v2-候选.md", "定稿的正文。")
        other = self._draft("第004章-处境卡.md")
        result = novel.adopt_chapter(self.project, 3, chosen)
        self.assertEqual((self.project / "正文" / "第003章.md").read_text(encoding="utf-8"), "定稿的正文。")
        self.assertEqual(len(result["moved"]), 3)
        self.assertTrue(other.exists())
        self.assertTrue((self.project / "待确认" / "已处理" / "第003章-v2-候选.md").exists())

    def test_adopt_refuses_to_overwrite_unless_asked_and_keeps_the_old_text(self):
        novel.init_project(self.project)
        novel.adopt_chapter(self.project, 1, self._draft("第001章-v2-候选.md", "第一版。"))
        again = self._draft("第001章-v3-候选.md", "第二版。")
        with self.assertRaises(FileExistsError):
            novel.adopt_chapter(self.project, 1, again)
        self.assertTrue(again.exists())
        result = novel.adopt_chapter(self.project, 1, again, replace=True)
        self.assertEqual((self.project / "正文" / "第001章.md").read_text(encoding="utf-8"), "第二版。")
        self.assertEqual(Path(result["backup"]).read_text(encoding="utf-8"), "第一版。")

    def test_adopt_rejects_an_empty_or_missing_file(self):
        novel.init_project(self.project)
        with self.assertRaises(ValueError):
            novel.adopt_chapter(self.project, 1, self._draft("第001章-v1-初稿.md", "# 只有标题\n"))
        with self.assertRaises(FileNotFoundError):
            novel.adopt_chapter(self.project, 1, self.project / "没有这个文件.md")
        self.assertEqual(novel.main(["adopt", str(self.project), "1", str(self.project / "没有.md")]), 1)

    def test_status_reports_chapters_gaps_and_pending_drafts(self):
        novel.init_project(self.project)
        novel.adopt_chapter(self.project, 1, self._draft("第001章-v2-候选.md", "一二三四五。"))
        novel.adopt_chapter(self.project, 3, self._draft("第003章-v2-候选.md", "一二三。"))
        self._draft("第004章-v1-初稿.md")
        status = novel.project_status(self.project)
        self.assertEqual(status["chapters"], {1: 6, 3: 4})
        self.assertEqual(status["latest"], 3)
        self.assertEqual(status["missing"], [2])
        self.assertEqual(status["pending"], ["第004章-v1-初稿.md"])


if __name__ == "__main__":
    unittest.main()
