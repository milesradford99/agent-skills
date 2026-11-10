#!/usr/bin/env python3
"""Bookkeeping for a webnovel-workflow project archive. Standard library only.

    novel.py init   <project>                      create the archive, never overwriting
    novel.py count  <file> [--target N]            count the characters of a chapter
    novel.py adopt  <project> <chapter> <file>     file an adopted chapter, archive its drafts
    novel.py diff   <candidate> <final>            list what the author changed, by paragraph
    novel.py status <project> [--target N]         adopted chapters, sizes, pending drafts

Nothing here deletes a file, and nothing edits 01-项目状态.md or the 记录-*.md
records: those describe the story and stay with the agent and the author.
"""

from __future__ import annotations

import argparse
import difflib
import re
import shutil
import sys
from pathlib import Path

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
    """Copy `source` to 正文/第NNN章.md and move the chapter's drafts to 待确认/已处理/."""
    if number < 1:
        raise ValueError("章号从 1 开始")
    if not source.is_file():
        raise FileNotFoundError(f"找不到采用的文件：{source}")
    text = source.read_text(encoding="utf-8")
    if count_chars(text) == 0:
        raise ValueError(f"{source} 里没有正文")
    body = project / BODY_DIR
    pending = project / PENDING_DIR
    done = pending / DONE_DIR
    target = body / f"{chapter_name(number)}.md"
    if target.exists() and not replace:
        raise FileExistsError(f"{target} 已经存在；确认要换版本就加 --replace，旧正文会留档")
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
    return {"target": target, "chars": count_chars(text), "moved": moved, "backup": backup}


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
    print("还没做：按采用的正文更新各份记录和 01-项目状态.md，核对后再把回写标成完成。")
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

    p = sub.add_parser("adopt", help="存正文，把这一章的旧稿挪去留档")
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
