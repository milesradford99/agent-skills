#!/usr/bin/env python3
"""Bookkeeping for a webnovel-workflow project archive. Standard library only.

    novel.py init   <project>                      create the archive, never overwriting
    novel.py count  <file> [--target N]            count the characters of a chapter
    novel.py adopt  <project> <chapter> <file>     file an adopted chapter, snapshot records, open the write-back
    novel.py diff   <candidate> <final>            list what the author changed, by paragraph
    novel.py status <project> [--target N]         adopted chapters, sizes, pending drafts
    novel.py check  <project>                      read-only check of status, records and sizes
    novel.py brief  <project> <chapter>            write the chapter's context pack to 待确认/
    novel.py done   <project>                      close the write-back once check is clean

Nothing here deletes a file or edits the story records (02–04, 记录-*.md): those stay
with the agent and the author. `adopt` and `done` own the progress fields of
01-项目状态.md (已采用到, the candidate pointers, 最近一次回写, 下一步) so they can't
drift from the files. `check`, `brief` and the status helpers live in context.py.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import context  # noqa: E402

REFERENCES = Path(__file__).resolve().parent.parent
TEMPLATES = REFERENCES / "templates"
RULES = REFERENCES / "写作规则-默认版.md"
RULES_NAME = "00-写作规则.md"
OPTIONAL_TEMPLATES = ("记录-资源.md",)
BODY_DIR = "正文"
PENDING_DIR = "待确认"
DONE_DIR = "已处理"
CHAPTER_RE = re.compile(r"^第0*(\d+)章")
NOTES_RE = re.compile(r"^#*\s*待确认事项")
TOLERANCE = 0.2
SIMILAR = 0.5  # below this, two paragraphs are not the same paragraph rewritten


def chapter_name(number: int) -> str:
    return f"第{number:03d}章"


def body_text(text: str) -> str:
    """The prose of a chapter: no headings, nothing after a 待确认事项 section."""
    lines = []
    for line in text.splitlines():
        if NOTES_RE.match(line.strip()):
            break
        if line.lstrip().startswith("#"):
            continue
        lines.append(line)
    return "\n".join(lines)


def count_chars(text: str) -> int:
    """Characters of prose, punctuation included, whitespace excluded."""
    return sum(1 for ch in body_text(text) if not ch.isspace())


def compare_to_target(count: int, target: int) -> str:
    if target <= 0:
        return ""
    ratio = (count - target) / target
    if abs(ratio) <= TOLERANCE:
        return f"目标 {target}，在两成以内"
    return f"目标 {target}，{'多' if ratio > 0 else '少'}了 {abs(ratio):.0%}"


def paragraphs(text: str) -> list[str]:
    return [line.strip() for line in body_text(text).splitlines() if line.strip()]


def pair_rewrites(before: list[str], after: list[str]) -> list[tuple[str, str, str]]:
    """Inside a changed block, pair each old paragraph with the rewrite of it, in order.

    A paragraph with no close counterpart is a deletion or an addition, not a rewrite.
    """
    changes: list[tuple[str, str, str]] = []
    start = 0
    for x in before:
        best, best_ratio = -1, SIMILAR
        for j in range(start, len(after)):
            ratio = difflib.SequenceMatcher(None, x, after[j], autojunk=False).ratio()
            if ratio > best_ratio:
                best, best_ratio = j, ratio
        if best < 0:
            changes.append(("删", x, ""))
            continue
        changes.extend(("加", "", y) for y in after[start:best])
        changes.append(("改", x, after[best]))
        start = best + 1
    changes.extend(("加", "", y) for y in after[start:])
    return changes


def diff_paragraphs(old: str, new: str) -> list[tuple[str, str, str]]:
    """Return (kind, before, after) for each change; kind is 删 / 加 / 改."""
    a, b = paragraphs(old), paragraphs(new)
    changes: list[tuple[str, str, str]] = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        before, after = a[i1:i2], b[j1:j2]
        if tag == "replace":
            changes.extend(pair_rewrites(before, after))
        elif tag == "delete":
            changes.extend(("删", x, "") for x in before)
        else:
            changes.extend(("加", "", y) for y in after)
    return changes


def free_path(path: Path) -> Path:
    """`path`, or the first `stem-2`, `stem-3` ... that doesn't exist yet."""
    if not path.exists():
        return path
    n = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not candidate.exists():
            return candidate
        n += 1


def init_project(project: Path, resources: bool = False) -> tuple[list[str], list[str]]:
    """Copy the templates into `project`. Return (created, kept) file names."""
    if not TEMPLATES.is_dir() or not RULES.is_file():
        raise FileNotFoundError(f"模板不在 {REFERENCES}，Skill 可能没装全")
    project.mkdir(parents=True, exist_ok=True)
    created, kept = [], []
    sources = [(RULES, RULES_NAME)]
    for template in sorted(TEMPLATES.glob("*.md")):
        if template.name in OPTIONAL_TEMPLATES and not resources:
            continue
        sources.append((template, template.name))
    for source, name in sources:
        target = project / name
        if target.exists():
            kept.append(name)
        else:
            shutil.copyfile(source, target)
            created.append(name)
    for folder in (BODY_DIR, PENDING_DIR):
        (project / folder).mkdir(exist_ok=True)
    return created, kept


def adopt_chapter(project: Path, number: int, source: Path, replace: bool = False) -> dict[str, object]:
    """File an adopted chapter and open its write-back.

    Copies `source` to 正文/第NNN章.md, snapshots the records, moves the chapter's drafts
    to 待确认/已处理/, and updates the progress fields of 01-项目状态.md. All checks run
    before anything is touched, so a refusal leaves the archive as it was.
    """
    if number < 1:
        raise ValueError("章号从 1 开始")
    if not source.is_file():
        raise FileNotFoundError(f"找不到采用的文件：{source}")
    text = source.read_text(encoding="utf-8")
    if count_chars(text) == 0:
        raise ValueError(f"{source} 里没有正文")
    status_path = project / context.STATUS
    if not status_path.is_file():
        raise FileNotFoundError(f"{project} 里没有 {context.STATUS}：不是小说档案，或者还没建档")
    status_text = status_path.read_text(encoding="utf-8-sig")
    open_writeback = context.writeback_in_progress(status_text)
    if open_writeback is not None:
        raise ValueError(f"第{open_writeback}章的回写还没完成：先补完并跑 novel.py done，再采用新的一章")
    body = project / BODY_DIR
    pending = project / PENDING_DIR
    done = pending / DONE_DIR
    target = body / f"{chapter_name(number)}.md"
    adopted = context.adopted_chapters(project)
    latest = adopted[-1] if adopted else 0
    if target.exists() and not replace:
        raise FileExistsError(f"{target} 已经存在；确认要换版本就加 --replace，旧正文会留档")
    if not target.exists() and number != latest + 1:
        raise ValueError(f"正文已采用到第{latest}章，下一章应该是第{latest + 1}章，不是第{number}章")

    try:
        relative = source.resolve().relative_to(project.resolve())
    except ValueError:
        relative = source
    files = "、".join(context.RECORDS_TO_UPDATE)
    updated = status_text
    for section, key, value in (
        ("现在在哪", "下一步", f"回写第{number}章：按采用的正文更新记录和交接，再跑 novel.py done"),
        ("正文进度", "已采用到", f"第{number}章"),
        ("正文进度", "正在写", "无"),
        ("正文进度", "这一章的进度", "无"),
        ("正文进度", "这一章的自检", "无"),
        ("正文进度", "完整初稿", "无"),
        ("正文进度", "当前唯一候选", "无"),
        ("最近一次回写", "来源章节和采用的文件", f"第{number}章，{relative}"),
        ("最近一次回写", "状态", "进行中"),
        ("最近一次回写", "要更新的文件", f"{files}（有变化的才改；有资源记录的加上 {context.RESOURCES}）"),
        ("最近一次回写", "改过的文件", "无（novel.py done 时填）"),
    ):
        updated = context.set_field(updated, section, key, value)

    snapshot = context.take_snapshot(project, number, replace)
    body.mkdir(parents=True, exist_ok=True)
    done.mkdir(parents=True, exist_ok=True)
    backup = None
    if target.exists():
        backup = free_path(done / f"{chapter_name(number)}-旧正文.md")
        shutil.move(str(target), str(backup))
    shutil.copyfile(source, target)
    moved = []
    for draft in sorted(pending.glob("*")):
        match = CHAPTER_RE.match(draft.name)
        if draft.is_file() and match and int(match.group(1)) == number:
            destination = free_path(done / draft.name)
            shutil.move(str(draft), str(destination))
            moved.append(destination.name)
    status_path.write_text(updated, encoding="utf-8")
    return {"target": target, "chars": count_chars(text), "moved": moved, "backup": backup, "snapshot": snapshot}


def finish_writeback(project: Path) -> dict[str, object]:
    """Close the write-back in progress if `check` is clean. Returns errors instead of raising."""
    status_path = project / context.STATUS
    status_text = status_path.read_text(encoding="utf-8-sig")
    number = context.writeback_in_progress(status_text)
    if number is None:
        raise ValueError("没有进行中的回写")
    errors, warnings = context.check_project(project, finishing=True)
    if errors:
        return {"closed": False, "chapter": number, "errors": errors, "warnings": warnings}
    changed, unchanged = context.writeback_changes(project, number)
    fields = context.status_fields(status_text)
    outline_numbers = [n for n, _, _ in context.current_outlines((project / context.OUTLINE).read_text(encoding="utf-8-sig"))]
    remaining = [n for n in outline_numbers if n > number]
    if fields.get("当前卷写到最后一章", "").startswith("是"):
        stage, step = "卷末", "卷末第 1 步：检查许给读者的事（读 卷末和完本.md）"
    elif number + 1 in outline_numbers:
        stage, step = "写正文", f"写第{number + 1}章"
    else:
        stage, step = "写正文", f"细纲用完了：先排第{number + 1}章起的细纲（读 排细纲.md），作者确认后再写"
    updated = status_text
    for section, key, value in (
        ("现在在哪", "当前阶段", stage),
        ("现在在哪", "下一步", step),
        ("最近一次回写", "状态", "完成"),
        ("最近一次回写", "改过的文件", "、".join(changed) or "无"),
    ):
        updated = context.set_field(updated, section, key, value)
    status_path.write_text(updated, encoding="utf-8")
    if 0 < len(remaining) < 3 and stage == "写正文":
        warnings.append(f"细纲只剩 {len(remaining)} 章：提醒作者排下一批")
    return {"closed": True, "chapter": number, "errors": [], "warnings": warnings,
            "changed": changed, "unchanged": unchanged, "next": step}


def project_status(project: Path) -> dict[str, object]:
    chapters: dict[int, int] = {}
    body = project / BODY_DIR
    if body.is_dir():
        for path in body.glob("*.md"):
            match = CHAPTER_RE.match(path.name)
            if match:
                chapters[int(match.group(1))] = count_chars(path.read_text(encoding="utf-8"))
    pending_dir = project / PENDING_DIR
    pending = sorted(p.name for p in pending_dir.glob("*") if p.is_file()) if pending_dir.is_dir() else []
    latest = max(chapters) if chapters else 0
    missing = [n for n in range(1, latest + 1) if n not in chapters]
    return {"chapters": chapters, "latest": latest, "missing": missing, "pending": pending}


def cmd_init(args: argparse.Namespace) -> int:
    created, kept = init_project(Path(args.project), args.resources)
    print(f"建好：{'、'.join(created) if created else '无'}；{BODY_DIR}/、{PENDING_DIR}/")
    if kept:
        print(f"已经有、没动：{'、'.join(kept)}")
    return 0


def cmd_count(args: argparse.Namespace) -> int:
    count = count_chars(Path(args.file).read_text(encoding="utf-8"))
    note = compare_to_target(count, args.target)
    print(f"{count} 字" + (f"（{note}）" if note else ""))
    return 0


def cmd_adopt(args: argparse.Namespace) -> int:
    result = adopt_chapter(Path(args.project), args.chapter, Path(args.file), args.replace)
    print(f"正文：{result['target']}（{result['chars']} 字）")
    if result["backup"]:
        print(f"旧正文留档：{result['backup']}")
    moved = result["moved"]
    print(f"挪进 {PENDING_DIR}/{DONE_DIR}/：{'、'.join(moved) if moved else '无'}")
    print(f"记录快照：{result['snapshot']}")
    print("项目状态已改：已采用到、候选清空、回写标“进行中”。")
    print("还没做：按采用的正文更新各份记录和交接，然后跑 novel.py done。")
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    result = finish_writeback(Path(args.project))
    for line in result["errors"]:
        print(f"错误：{line}")
    for line in result["warnings"]:
        print(f"提醒：{line}")
    if not result["closed"]:
        print(f"第{result['chapter']}章的回写还没完成，上面的错误改完再跑一次。")
        return 1
    print(f"第{result['chapter']}章回写完成。改过的：{'、'.join(result['changed']) or '无'}；没动的：{'、'.join(result['unchanged']) or '无'}")
    print(f"下一步：{result['next']}")
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    old = Path(args.candidate).read_text(encoding="utf-8")
    new = Path(args.final).read_text(encoding="utf-8")
    changes = diff_paragraphs(old, new)
    tally = {kind: sum(1 for c in changes if c[0] == kind) for kind in ("删", "加", "改")}
    print(f"候选 {count_chars(old)} 字，终稿 {count_chars(new)} 字；删 {tally['删']} 段，加 {tally['加']} 段，改 {tally['改']} 段")
    for kind, before, after in changes:
        print()
        if kind == "改":
            similarity = difflib.SequenceMatcher(None, before, after, autojunk=False).ratio()
            print(f"[改，相似 {similarity:.0%}]")
            print(f"  原：{before}")
            print(f"  终：{after}")
        elif kind == "删":
            print(f"[删]\n  原：{before}")
        else:
            print(f"[加]\n  终：{after}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    status = project_status(Path(args.project))
    chapters: dict[int, int] = status["chapters"]  # type: ignore[assignment]
    if not chapters:
        print("正文：还没有已采用的章")
    else:
        total = sum(chapters.values())
        print(f"正文：{len(chapters)} 章，最新第 {status['latest']} 章，共 {total} 字，平均 {total // len(chapters)} 字")
        if status["missing"]:
            print(f"缺章：{'、'.join(str(n) for n in status['missing'])}")
        if args.target > 0:
            off = [f"第{n}章 {c} 字" for n, c in sorted(chapters.items()) if abs(c - args.target) > args.target * TOLERANCE]
            if off:
                print(f"和目标 {args.target} 差出两成以上：{'；'.join(off)}")
    pending = status["pending"]
    print(f"{PENDING_DIR}/ 里没处理的：{'、'.join(pending) if pending else '无'}")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    errors, warnings = context.check_project(Path(args.project))
    for line in errors:
        print(f"错误：{line}")
    for line in warnings:
        print(f"提醒：{line}")
    if not errors and not warnings:
        print("没查出问题")
    else:
        print(f"共 {len(errors)} 个错误、{len(warnings)} 个提醒。错误先处理完再动笔。")
    return 1 if errors else 0


def cmd_brief(args: argparse.Namespace) -> int:
    project = Path(args.project)
    if args.stdout:
        print(context.build_brief(project, args.chapter).text, end="")
        return 0
    path, brief = context.write_brief(project, args.chapter, Path(args.out) if args.out else None)
    manifest = brief.manifest
    print(f"资料包：{path}（{manifest['chars']} 字）")
    print(f"带上的条目：{'、'.join(manifest['mentioned']) or '无'}；伏笔：{'、'.join(manifest['threads']) or '无'}")
    if not manifest["outline"]:
        print(f"注意：{context.OUTLINE} 里没有第{args.chapter}章的细纲")
    if manifest["not_found"]:
        print(f"没找到条目的名字：{'、'.join(manifest['not_found'])}")
    if manifest["unknown_ids"]:
        print(f"细纲提到、没收的伏笔里没有：{'、'.join(manifest['unknown_ids'])}")
    for flag in manifest["flagged"]:
        print(f"注意：{flag}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="长篇网文项目档案的记账工具")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", help="建档，不覆盖已有文件")
    p.add_argument("project")
    p.add_argument("--resources", action="store_true", help="同时建 记录-资源.md")
    p.set_defaults(func=cmd_init)

    p = sub.add_parser("count", help="数正文字数")
    p.add_argument("file")
    p.add_argument("--target", type=int, default=0)
    p.set_defaults(func=cmd_count)

    p = sub.add_parser("adopt", help="存正文、快照记录、旧稿留档，并在项目状态里登记回写")
    p.add_argument("project")
    p.add_argument("chapter", type=int)
    p.add_argument("file")
    p.add_argument("--replace", action="store_true", help="正文里已有这一章时换掉它，旧的留档")
    p.set_defaults(func=cmd_adopt)

    p = sub.add_parser("diff", help="按段对比候选稿和作者终稿")
    p.add_argument("candidate")
    p.add_argument("final")
    p.set_defaults(func=cmd_diff)

    p = sub.add_parser("status", help="已采用章数、字数和没处理的候选")
    p.add_argument("project")
    p.add_argument("--target", type=int, default=0)
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("done", help="check 干净后把回写标成完成，并写好下一步")
    p.add_argument("project")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("check", help="只读检查项目状态、记录和文件大小，有错误时返回 1")
    p.add_argument("project")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("brief", help="按细纲和上一章结尾抽出这一章要读的资料，存进 待确认/")
    p.add_argument("project")
    p.add_argument("chapter", type=int)
    p.add_argument("--out", help="写到别的路径")
    p.add_argument("--stdout", action="store_true", help="只打印，不写文件")
    p.set_defaults(func=cmd_brief)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError) as err:
        print(f"没做成：{err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
