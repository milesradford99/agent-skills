"""Tests for the webnovel-workflow bookkeeping tool. Run with: python3 -m unittest discover -s tests"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "webnovel-workflow" / "references" / "tools"))

import context  # noqa: E402
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


def write(project, name, text):
    path = Path(project) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def sample_book(project):
    """A small archive at chapter 3, with an outline for chapter 4."""
    novel.init_project(project)
    write(project, "03-人物.md", "# 人物\n\n## 林晚\n- 别名：师姐、林师姐\n- 身份：外门弟子\n\n"
          "## 林晚晴\n- 别名：无\n- 身份：林晚的堂妹\n\n## 顾长风\n- 别名：顾师兄\n- 身份：首席\n\n"
          "## 赵三\n- 别名：无\n- 身份：杂役\n\n## 周\n- 别名：无\n- 身份：一字名\n")
    write(project, "记录-人物现状.md", "# 人物现状\n\n## 林晚\n- 状态：在场\n- 现在在哪：药园\n\n"
          "## 林晚晴\n- 状态：离场\n\n## 顾长风\n- 状态：在场\n\n## 赵三\n- 状态：死亡\n\n## 周\n- 状态：在场\n")
    write(project, "02-设定.md", "# 设定\n\n## 重要地点和物品\n### 九转丹方\n- 别名：丹方\n- 是什么：秘传\n\n"
          "### 藏经阁\n- 别名：无\n- 是什么：不相干的地方\n\n## 尚未揭示\n- 顾长风是掌门私生子\n")
    write(project, "记录-伏笔.md", "# 伏笔\n\n## 没收的\n### F001\n- 涉及：九转丹方\n- 内容：少了一页\n\n"
          "### F002\n- 涉及：执事\n- 内容：执事的旧伤\n\n### F004\n- 涉及：藏经阁\n- 内容：无关\n\n"
          "## 已收的\n### F003\n- 涉及：赵三\n- 内容：欠债\n")
    write(project, "记录-废弃设定.md", "# 废弃设定\n\n## D001\n- 原来是什么：顾长风是林晚的亲哥哥\n\n"
          "## D002\n- 原来是什么：藏经阁有阵法\n")
    write(project, "记录-时间线.md", "# 时间线\n\n- 第001章：入门\n- 第002章：失窃\n- 第003章：受伤\n- 第004章：待填写\n")
    write(project, "04-大纲.md", "# 大纲\n\n## 当前细纲\n### 第4章：对质\n- 出场：师姐、顾师兄、执事\n"
          "- 伏笔：F001、F009\n- 师姐撞见他翻找丹方。\n\n### 第5章：夜审\n- 伏笔：F003\n- 赵三的鬼魂出现。\n")
    for n in (1, 2, 3):
        write(project, f"正文/第{n:03d}章.md", f"# 第{n}章\n\n第{n}章开头。\n\n第{n}章结尾，林晚晴走了。\n")
    status = (Path(project) / "01-项目状态.md").read_text(encoding="utf-8")
    status = status.replace("- 已采用到：无（第几章）", "- 已采用到：第3章")
    status = status.replace("- 定稿参照章：无（前三章采用后由作者挑一章，写明第几章；管腔调，可以换）", "- 定稿参照章：第2章")
    status = status.replace("- 更新于：无（日期，第几章前后）", "- 更新于：11-13，第3章后")
    status = status.replace("- 作者最近的指示：无（每条写日期，比如“11-13：这一卷感情线放慢，第40章前不让两人和好”）",
                            "- 作者最近的指示：11-13：第4章别让林晚当场揭穿")
    write(project, "01-项目状态.md", status)


class BriefTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name) / "书"
        sample_book(self.project)

    def test_pulls_only_the_entries_the_chapter_needs(self):
        brief = context.build_brief(self.project, 4)
        mentioned = brief.manifest["mentioned"]
        for name in ("林晚", "顾长风", "九转丹方", "林晚晴"):
            self.assertIn(name, mentioned)
        self.assertNotIn("藏经阁", mentioned)
        self.assertNotIn("赵三", mentioned)
        self.assertIn("### F001", brief.text)
        self.assertIn("### F002", brief.text, "a listed name missing from the archive still pulls its records")
        self.assertNotIn("### F004", brief.text)
        self.assertIn("### D001", brief.text)
        self.assertNotIn("### D002", brief.text)

    def test_longer_names_win_over_their_prefixes(self):
        index = context.NameIndex(context.parse_entries(
            (self.project / "03-人物.md").read_text(encoding="utf-8"), "03-人物.md"))
        self.assertEqual(index.scan("林晚晴推门进来"), ["林晚晴"])
        self.assertIn("周", index.short)

    def test_manifest_reports_gaps_and_the_handover_is_trimmed(self):
        brief = context.build_brief(self.project, 4)
        self.assertEqual(brief.manifest["not_found"], ["执事"])
        self.assertEqual(brief.manifest["unknown_ids"], ["F009"])
        self.assertIn("第4章别让林晚当场揭穿", brief.text)
        self.assertNotIn("当前张力", brief.text, "empty handover fields are dropped")
        self.assertIn("顾长风是掌门私生子", brief.text)
        self.assertIn("第003章：受伤", brief.text)
        self.assertNotIn("第004章：待填写", brief.text)
        self.assertIn("第3章结尾", brief.text)
        self.assertIn("正文/第002章.md", brief.text)

    def test_write_brief_goes_to_pending_and_adopt_files_it_away(self):
        path, _ = context.write_brief(self.project, 4)
        self.assertEqual(path, self.project / "待确认" / "第004章-资料包.md")
        draft = write(self.project, "待确认/第004章-v2-候选.md", "定稿。")
        novel.adopt_chapter(self.project, 4, draft)
        self.assertTrue((self.project / "待确认" / "已处理" / "第004章-资料包.md").exists())

    def test_missing_outline_and_old_archive_degrade_without_failing(self):
        (self.project / "记录-伏笔.md").unlink()
        brief = context.build_brief(self.project, 9)
        self.assertFalse(brief.manifest["outline"])
        self.assertIn("记录-伏笔.md", brief.manifest["missing_files"])
        with self.assertRaises(FileNotFoundError):
            context.build_brief(Path(self._tmp.name) / "空", 1)


class CheckTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.project = Path(self._tmp.name) / "书"

    def test_a_fresh_archive_is_clean(self):
        novel.init_project(self.project)
        errors, warnings = context.check_project(self.project)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_finds_the_problems_a_new_session_would_trip_on(self):
        sample_book(self.project)
        write(self.project, "正文/第005章.md", "跳章。")
        write(self.project, "待确认/第002章-v3-候选.md", "旧稿。")
        status = (self.project / "01-项目状态.md").read_text(encoding="utf-8")
        status = status.replace("- 状态：无（进行中／完成）", "- 状态：进行中")
        status = status.replace("- 当前唯一候选：无（文件路径）", "- 当前唯一候选：待确认/第006章-v2-候选.md")
        write(self.project, "01-项目状态.md", status)
        errors, warnings = context.check_project(self.project)
        joined = "\n".join(errors)
        self.assertIn("已采用到第3章", joined)
        self.assertIn("缺章：第4章", joined)
        self.assertIn("进行中", joined)
        self.assertIn("第006章-v2-候选.md 不存在", joined)
        self.assertIn("F009", joined)
        notes = "\n".join(warnings)
        self.assertIn("F003", notes)
        self.assertIn("赵三", notes)
        self.assertIn("第002章-v3-候选.md", notes)
        self.assertIn("「第5章：夜审」没有“出场”", notes)
        self.assertEqual(novel.main(["check", str(self.project)]), 1)

    def test_old_archive_without_handover_only_warns(self):
        sample_book(self.project)
        status = (self.project / "01-项目状态.md").read_text(encoding="utf-8")
        start, end = status.index("## 交接"), status.index("## 开书进度")
        write(self.project, "01-项目状态.md", status[:start] + status[end:])
        write(self.project, "04-大纲.md", "# 大纲\n")
        errors, warnings = context.check_project(self.project)
        self.assertEqual(errors, [])
        self.assertTrue(any("交接" in line for line in warnings))

    def test_size_caps_and_duplicate_ids(self):
        sample_book(self.project)
        write(self.project, "记录-伏笔.md", "# 伏笔\n\n## 没收的\n### F001\n- 内容：a\n\n### F001\n- 内容：b\n")
        write(self.project, "记录-人物现状.md", "# 人物现状\n\n" + "很长的记录。" * 4000)
        errors, warnings = context.check_project(self.project)
        self.assertTrue(any("编号重复：F001" in line for line in errors))
        self.assertTrue(any(line.startswith("记录-人物现状.md 有") for line in warnings))


if __name__ == "__main__":
    unittest.main()
