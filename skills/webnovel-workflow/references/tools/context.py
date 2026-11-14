"""Read a webnovel-workflow archive: build a chapter's context pack and check the archive.

Used by novel.py (`brief`, `check`). Standard library only, read-only: nothing here
writes to the archive except `write_brief`, which writes one derived file into 待确认/.

Archive conventions this relies on (the templates set them up, `check` enforces them):
- An entry is a markdown heading (## or deeper) whose title is a name, followed by
  `- 别名：…` on one of its lines. Headings in SECTION_TITLES are sections, not entries.
- A chapter outline is a heading `### 第N章：…` with `- 出场：…` and `- 伏笔：…` lines.
- Status fields are `- 键：值` lines in 01-项目状态.md; the handover is its `## 交接` section.
"""

from __future__ import annotations

import filecmp
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

STATUS = "01-项目状态.md"
RULES = "00-写作规则.md"
SETTINGS = "02-设定.md"
CHARACTERS = "03-人物.md"
OUTLINE = "04-大纲.md"
CURRENT = "记录-人物现状.md"
FORESHADOW = "记录-伏笔.md"
TIMELINE = "记录-时间线.md"
DROPPED = "记录-废弃设定.md"
RESOURCES = "记录-资源.md"
BODY_DIR = "正文"
PENDING_DIR = "待确认"
DONE_DIR = "已处理"
CORE_FILES = (STATUS, RULES, SETTINGS, CHARACTERS, OUTLINE, CURRENT, FORESHADOW, TIMELINE, DROPPED)
SNAPSHOT_FILES = (STATUS, SETTINGS, CHARACTERS, OUTLINE, CURRENT, FORESHADOW, TIMELINE, DROPPED, RESOURCES)
RECORDS_TO_UPDATE = (CURRENT, FORESHADOW, TIMELINE, CHARACTERS, SETTINGS, OUTLINE)

SECTION_TITLES = {
    "世界与生活", "能力、技术或制度", "重要地点和物品", "尚未揭示", "待定",
    "没收的", "已收的", "故事框架", "作者确认的卖点", "分卷纲", "当前细纲", "已写",
    "现在在哪", "交接", "开书进度", "正文进度", "卷末进度", "最近一次回写", "约定",
}
PLACEHOLDER_TITLES = {"人物名", "地点或物品名"}
NONE_VALUES = {"", "无", "没有", "待填写", "待定"}
MIN_NAME = 2  # one-character names would match almost every sentence
PREVIOUS_TAIL = 1500
RECENT_TIMELINE = 3
BRIEF_LIMIT = 40000

# Soft caps, in characters. Past these the "read only what's needed" rule stops working.
SIZE_CAPS = {
    STATUS: 6000,
    RULES: 20000,
    CURRENT: 20000,
    FORESHADOW: 15000,
    TIMELINE: 8000,
    SETTINGS: 30000,
    CHARACTERS: 30000,
}
HANDOVER_CAP = 2000

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FIELD_RE = re.compile(r"^\s*[-*]\s*([^：:\n]{1,20})[：:]\s*(.*)$")
CHAPTER_HEADING_RE = re.compile(r"^第0*(\d+)章")
CHAPTER_FILE_RE = re.compile(r"^第0*(\d+)章")
FORESHADOW_ID_RE = re.compile(r"\bF\d{3,}\b")
NUMBER_RE = re.compile(r"\d+")
SPLIT_RE = re.compile(r"[、，,；;/\s]+")


@dataclass
class Entry:
    source: str
    title: str
    level: int
    section: str
    lines: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines).strip()

    def field(self, key: str) -> str:
        return field_value(self.lines, key)

    @property
    def aliases(self) -> list[str]:
        return split_names(self.field("别名"))

    @property
    def names(self) -> list[str]:
        return [self.title, *self.aliases]

    def as_block(self, level: int = 3) -> str:
        body = self.lines[1:] if self.lines and HEADING_RE.match(self.lines[0]) else self.lines
        return "\n".join([f"{'#' * level} {self.title}", *body]).strip()


def is_none(value: str) -> bool:
    value = value.strip()
    return value in NONE_VALUES or value.startswith("无（") or value.startswith("无(")


def split_names(value: str) -> list[str]:
    if is_none(value):
        return []
    return [part for part in SPLIT_RE.split(value.strip()) if part and not is_none(part)]


def field_value(lines: list[str], key: str) -> str:
    for line in lines:
        match = FIELD_RE.match(line)
        if match and match.group(1).strip() == key:
            return match.group(2).strip()
    return ""


def read(project: Path, name: str) -> str | None:
    path = project / name
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8-sig")


def headings(text: str) -> list[tuple[int, int, str]]:
    """(line index, level, title) for every heading, skipping fenced code."""
    found, fenced = [], False
    for index, line in enumerate(text.splitlines()):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        match = None if fenced else HEADING_RE.match(line)
        if match:
            found.append((index, len(match.group(1)), match.group(2).strip()))
    return found


def section(text: str, predicate) -> tuple[str, list[str]] | None:
    """The first heading whose title satisfies `predicate`, with its lines up to the next
    heading of the same or a higher level."""
    lines = text.splitlines()
    marks = headings(text)
    for position, (index, level, title) in enumerate(marks):
        if predicate(title):
            end = len(lines)
            for later_index, later_level, _ in marks[position + 1:]:
                if later_level <= level:
                    end = later_index
                    break
            return title, lines[index:end]
    return None


def named_section(text: str, name: str) -> list[str] | None:
    found = section(text, lambda title: title == name)
    return found[1] if found else None


def parse_entries(text: str, source: str) -> list[Entry]:
    lines = text.splitlines()
    marks = headings(text)
    entries: list[Entry] = []
    parents: dict[int, str] = {}
    for position, (index, level, title) in enumerate(marks):
        parents[level] = title
        for deeper in [lvl for lvl in parents if lvl > level]:
            del parents[deeper]
        if level < 2 or title in SECTION_TITLES or title in PLACEHOLDER_TITLES:
            continue
        end = len(lines)
        for later_index, later_level, _ in marks[position + 1:]:
            if later_level <= level:
                end = later_index
                break
        parent = next((parents[lvl] for lvl in sorted(parents, reverse=True) if lvl < level), "")
        entries.append(Entry(source, title, level, parent, lines[index:end]))
    return entries


def status_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = FIELD_RE.match(line)
        if match:
            fields.setdefault(match.group(1).strip(), match.group(2).strip())
    return fields


def chapter_number(value: str) -> int | None:
    if is_none(value):
        return None
    match = NUMBER_RE.search(value)
    return int(match.group()) if match else None


def adopted_chapters(project: Path) -> list[int]:
    body = project / BODY_DIR
    if not body.is_dir():
        return []
    numbers = []
    for path in body.glob("*.md"):
        match = CHAPTER_FILE_RE.match(path.name)
        if match:
            numbers.append(int(match.group(1)))
    return sorted(numbers)


def chapter_outline(outline_text: str, number: int) -> tuple[str, list[str]] | None:
    def is_this_chapter(title: str) -> bool:
        match = CHAPTER_HEADING_RE.match(title)
        return bool(match and int(match.group(1)) == number)

    return section(outline_text, is_this_chapter)


def current_outlines(outline_text: str) -> list[tuple[int, str, list[str]]]:
    lines = named_section(outline_text, "当前细纲")
    if not lines:
        return []
    block = "\n".join(lines)
    found = []
    for entry in parse_entries(block, OUTLINE):
        match = CHAPTER_HEADING_RE.match(entry.title)
        if match:
            found.append((int(match.group(1)), entry.title, entry.lines))
    return found


class NameIndex:
    """Every entry name and alias from the character and setting files, for mention scans."""

    def __init__(self, entries: list[Entry]):
        self.canonical: dict[str, str] = {}
        self.short: set[str] = set()
        for entry in entries:
            for name in entry.names:
                if len(name) < MIN_NAME:
                    self.short.add(name)
                    continue
                self.canonical.setdefault(name, entry.title)

    def knows(self, name: str) -> bool:
        return name in self.canonical

    def scan(self, text: str) -> list[str]:
        """Canonical titles mentioned in `text`, longest names first so 林晚晴 isn't read as 林晚."""
        found: list[str] = []
        remaining = text
        for name in sorted(self.canonical, key=len, reverse=True):
            if name in remaining:
                title = self.canonical[name]
                if title not in found:
                    found.append(title)
                remaining = remaining.replace(name, "\0" * len(name))
        return found

    def variants(self, titles: list[str]) -> list[str]:
        wanted = set(titles)
        return [name for name, title in self.canonical.items() if title in wanted]


def tail(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    cut = text[-limit:]
    newline = cut.find("\n")
    return cut[newline + 1:].strip() if 0 <= newline < limit // 2 else cut.strip()


def prose(text: str) -> str:
    kept = []
    for line in text.splitlines():
        if re.match(r"^#*\s*待确认事项", line.strip()):
            break
        if not line.lstrip().startswith("#"):
            kept.append(line)
    return "\n".join(kept)


def filled_fields(lines: list[str]) -> list[str]:
    """The `- 键：值` lines whose value is filled in; template prose and empty fields dropped."""
    kept = []
    for line in lines:
        match = FIELD_RE.match(line)
        if match and not is_none(match.group(2)):
            kept.append(line.strip())
    return kept


def mentions_any(entry: Entry, names: list[str]) -> bool:
    text = entry.text
    return any(name in text for name in names)


@dataclass
class Brief:
    chapter: int
    text: str
    manifest: dict[str, object]


def build_brief(project: Path, number: int, today: date | None = None) -> Brief:
    if number < 1:
        raise ValueError("章号从 1 开始")
    if read(project, STATUS) is None:
        raise FileNotFoundError(f"{project} 里没有 {STATUS}，不是小说档案，或者还没建档")
    notes: list[str] = []
    missing_files = [name for name in CORE_FILES if read(project, name) is None]
    if missing_files:
        raise FileNotFoundError(f"档案缺文件：{'、'.join(missing_files)}（用 novel.py init 补建）")

    status_text = read(project, STATUS) or ""
    fields = status_fields(status_text)
    handover = named_section(status_text, "交接")
    if handover is None:
        raise ValueError(f"{STATUS} 没有“交接”一节，照模板补上再跑")

    outline_text = read(project, OUTLINE) or ""
    outline = chapter_outline(outline_text, number)
    if outline is None:
        raise ValueError(f"{OUTLINE} 里没有第{number}章的细纲：先按 排细纲.md 排、查、交作者确认")
    outline_lines = outline[1]
    if not field_value(outline_lines, "出场") or not field_value(outline_lines, "伏笔"):
        raise ValueError(f"第{number}章的细纲缺“出场”或“伏笔”一行，补上再跑（没有就写“无”）")
    listed = split_names(field_value(outline_lines, "出场"))
    outline_ids = sorted(set(FORESHADOW_ID_RE.findall("\n".join(outline_lines))))

    character_entries = parse_entries(read(project, CHARACTERS) or "", CHARACTERS)
    current_entries = parse_entries(read(project, CURRENT) or "", CURRENT)
    setting_text = read(project, SETTINGS) or ""
    setting_entries = parse_entries(setting_text, SETTINGS)
    index = NameIndex(character_entries + current_entries + setting_entries)

    previous_text = ""
    previous_whole = False
    previous_path = project / BODY_DIR / f"第{number - 1:03d}章.md"
    if number > 1:
        if previous_path.is_file():
            full = prose(previous_path.read_text(encoding="utf-8-sig")).strip()
            previous_text = tail(full, PREVIOUS_TAIL)
            previous_whole = previous_text == full
        else:
            notes.append(f"没有上一章正文 {BODY_DIR}/{previous_path.name}")

    scan_text = "\n".join(outline_lines[1:]) + "\n" + previous_text
    mentioned = index.scan(scan_text)
    for name in listed:
        if index.knows(name) and index.canonical[name] not in mentioned:
            mentioned.append(index.canonical[name])
    not_found = [name for name in listed if not index.knows(name)]
    # Names the outline lists but the archive lacks still pull in records that mention them.
    names = index.variants(mentioned) + [name for name in not_found if len(name) >= MIN_NAME]

    def pick(entries: list[Entry]) -> list[Entry]:
        return [entry for entry in entries if entry.title in mentioned]

    characters = pick(character_entries)
    current = pick(current_entries)
    settings = pick(setting_entries)
    special = {index.canonical.get(name, name) for name in
               split_names(re.sub(r"[（(][^）)]*[）)]", "", field_value(outline_lines, "特殊出场")))}
    flagged = [f"{entry.title} 在记录里是“{entry.field('状态')}”，细纲里却出场：没写“特殊出场”说明，先停下问作者"
               for entry in current
               if entry.field("状态")[:2] in ("死亡", "失踪") and entry.title not in special]

    unrevealed = named_section(setting_text, "尚未揭示")
    unrevealed_text = "\n".join(unrevealed[1:]).strip() if unrevealed else ""
    if unrevealed_text and all(is_none(line.lstrip("-* ").strip()) for line in unrevealed[1:] if line.strip()):
        unrevealed_text = ""

    foreshadow_entries = parse_entries(read(project, FORESHADOW) or "", FORESHADOW)
    open_threads = [entry for entry in foreshadow_entries if entry.section != "已收的"]
    closed_ids = {entry.title for entry in foreshadow_entries if entry.section == "已收的"}
    threads = [entry for entry in open_threads
               if entry.title in outline_ids or (names and mentions_any(entry, names))]
    known_ids = {entry.title for entry in open_threads}
    unknown_ids = [fid for fid in outline_ids if fid not in known_ids]

    dropped = [entry for entry in parse_entries(read(project, DROPPED) or "", DROPPED)
               if names and mentions_any(entry, names)]
    resources = [entry for entry in parse_entries(read(project, RESOURCES) or "", RESOURCES)
                 if names and mentions_any(entry, names)]

    timeline = []
    for line in (read(project, TIMELINE) or "").splitlines():
        match = re.match(r"^\s*[-*]\s*第0*(\d+)章", line)
        if match and int(match.group(1)) < number and "待填写" not in line:
            timeline.append(line.strip())
    timeline = timeline[-RECENT_TIMELINE:]

    reference = fields.get("定稿参照章", "")
    reference_number = chapter_number(reference)

    parts: list[str] = []

    def add(title: str, body: str) -> None:
        if body.strip():
            parts.append(f"## {title}\n\n{body.strip()}")

    handover_lines = filled_fields(handover[1:])
    if handover_lines:
        add("交接（上一次对话留下的）", "\n".join(handover_lines))
    add(f"这一章的细纲：{outline[0]}", "\n".join(outline_lines[1:]))
    if previous_text:
        label = "全文" if previous_whole else f"最后约 {len(previous_text)} 字"
        add(f"上一章{'' if previous_whole else '结尾'}（{BODY_DIR}/{previous_path.name} {label}）", previous_text)
    add("最近的时间线", "\n".join(timeline))
    add(f"人物（{CHARACTERS}）", "\n\n".join(entry.as_block() for entry in characters))
    add(f"人物现状（{CURRENT}）", "\n\n".join(entry.as_block() for entry in current))
    add(f"设定条目（{SETTINGS}）", "\n\n".join(entry.as_block() for entry in settings))
    add("尚未揭示（人物不能提前知道；不放进给独立读者的事实清单）", unrevealed_text)
    add(f"没收的伏笔（{FORESHADOW}）", "\n\n".join(entry.as_block() for entry in threads))
    add(f"和这一章有关的废弃设定（{DROPPED}，不要写回来）", "\n\n".join(entry.as_block() for entry in dropped))
    add(f"资源（{RESOURCES}）", "\n\n".join(entry.as_block() for entry in resources))

    manifest_lines = [
        f"- 细纲：{OUTLINE}「{outline[0]}」",
        f"- 细纲列出的出场：{'、'.join(listed) if listed else '无'}",
        f"- 带上的条目：{'、'.join(mentioned) if mentioned else '无'}",
    ]
    if not_found:
        manifest_lines.append(f"- 没找到条目的名字：{'、'.join(not_found)}（先核对写法和别名；确实是新人物，按细纲里“新加”的处理）")
    manifest_lines.append(f"- 伏笔：{'、'.join(entry.title for entry in threads) if threads else '无'}")
    if unknown_ids:
        closed = [fid for fid in unknown_ids if fid in closed_ids]
        absent = [fid for fid in unknown_ids if fid not in closed_ids]
        if absent:
            manifest_lines.append(f"- 细纲提到、伏笔记录里没有：{'、'.join(absent)}")
        if closed:
            manifest_lines.append(f"- 细纲提到、记录里已经收掉的：{'、'.join(closed)}")
    for flag in flagged:
        manifest_lines.append(f"- 注意：{flag}")
    if reference_number:
        manifest_lines.append(f"- 定稿参照章：第{reference_number}章（{BODY_DIR}/第{reference_number:03d}章.md），动笔前自己读")
    else:
        manifest_lines.append("- 定稿参照章：还没定（前三章期间按项目状态里的“写前参照”读）")
    target = fields.get("每章目标字数", "")
    if not is_none(target):
        manifest_lines.append(f"- 每章目标字数：{target}")
    manifest_lines.append("- 没带的：写作规则（开工时读过）、分卷纲（需要时读 04-大纲.md 当前卷一节）、旧章节全文（拿不准就按名字去翻正文）")
    if index.short:
        manifest_lines.append(f"- 太短没法扫的名字：{'、'.join(sorted(index.short))}（细纲里出现时自己去查）")
    if not handover_lines:
        manifest_lines.append("- 交接一节是空的")
    manifest_lines.extend(f"- {note}" for note in notes)

    body = "\n\n".join(parts)
    stamp = (today or date.today()).isoformat()
    header = (f"# 第{number:03d}章 资料包\n\n"
              f"novel.py brief 生成于 {stamp}，是从档案里抽出来的副本，不要改它，要改去改档案。"
              "写这一章读这份就够；资料里没有的旧事，去翻那一章的正文，不要凭摘要猜。")
    text = f"{header}\n\n## 清单\n\n" + "\n".join(manifest_lines) + (f"\n\n{body}" if body else "") + "\n"
    if len(text) > BRIEF_LIMIT:
        text = text.replace("\n## 清单\n\n", f"\n## 清单\n\n- 资料包有 {len(text)} 字，偏长：看看是不是某份记录该归档了\n", 1)
    manifest = {
        "outline": True, "listed": listed, "mentioned": mentioned, "not_found": not_found,
        "threads": [entry.title for entry in threads], "unknown_ids": unknown_ids,
        "flagged": flagged, "chars": len(text),
    }
    return Brief(number, text, manifest)


def write_brief(project: Path, number: int, out: Path | None = None) -> tuple[Path, Brief]:
    brief = build_brief(project, number)
    path = out or project / PENDING_DIR / f"第{number:03d}章-资料包.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(brief.text, encoding="utf-8")
    return path, brief


def snapshot_dir(project: Path, number: int) -> Path:
    return project / PENDING_DIR / DONE_DIR / f"快照-第{number:03d}章-采用前"


def take_snapshot(project: Path, number: int, replace: bool = False) -> Path:
    """Copy the records as they were before chapter `number` was written back."""
    folder = snapshot_dir(project, number)
    if folder.exists():
        if not replace:
            raise FileExistsError(f"{folder} 已经存在：第{number}章采用过一次，换版本要先问清作者")
        n = 2
        while folder.with_name(f"{folder.name}-被替换{n}").exists():
            n += 1
        folder.rename(folder.with_name(f"{folder.name}-被替换{n}"))
    folder.mkdir(parents=True)
    for name in SNAPSHOT_FILES:
        source = project / name
        if source.is_file():
            (folder / name).write_bytes(source.read_bytes())
    return folder


def writeback_changes(project: Path, number: int) -> tuple[list[str], list[str]]:
    """(changed, unchanged) record files compared with the snapshot taken when `number` was adopted."""
    folder = snapshot_dir(project, number)
    changed, unchanged = [], []
    for name in RECORDS_TO_UPDATE + (RESOURCES,):
        current, before = project / name, folder / name
        if not current.is_file():
            continue
        if before.is_file() and filecmp.cmp(current, before, shallow=False):
            unchanged.append(name)
        else:
            changed.append(name)
    return changed, unchanged


def set_field(text: str, section_name: str, key: str, value: str) -> str:
    """Replace the `- key：…` line inside `## section_name`. Raises if either is missing."""
    lines = text.splitlines()
    marks = headings(text)
    for position, (index, level, title) in enumerate(marks):
        if title != section_name:
            continue
        end = len(lines)
        for later_index, later_level, _ in marks[position + 1:]:
            if later_level <= level:
                end = later_index
                break
        for i in range(index + 1, end):
            match = FIELD_RE.match(lines[i])
            if match and match.group(1).strip() == key:
                lines[i] = f"- {key}：{value}"
                return "\n".join(lines) + "\n"
        raise ValueError(f"{STATUS} 的“{section_name}”里没有“{key}”一行")
    raise ValueError(f"{STATUS} 没有“{section_name}”一节")


def handover_chapter(handover: list[str]) -> int | None:
    match = re.search(r"第0*(\d+)章", field_value(handover, "更新于"))
    return int(match.group(1)) if match else None


def writeback_in_progress(status_text: str) -> int | None:
    """The chapter whose write-back is still 进行中, or None."""
    writeback = named_section(status_text, "最近一次回写")
    if writeback and field_value(writeback, "状态").startswith("进行中"):
        return chapter_number(field_value(writeback, "来源章节和采用的文件")) or 0
    return None


def chapter_mentions_stale(project: Path, number: int) -> list[str]:
    """Characters named in adopted chapter `number` whose 现状 entry was last updated before it."""
    chapter = project / BODY_DIR / f"第{number:03d}章.md"
    if not chapter.is_file():
        return []
    characters = parse_entries(read(project, CHARACTERS) or "", CHARACTERS)
    current = parse_entries(read(project, CURRENT) or "", CURRENT)
    index = NameIndex(characters + current)
    named = index.scan(prose(chapter.read_text(encoding="utf-8-sig")))
    stale = []
    for entry in current:
        if entry.title in named:
            updated = chapter_number(entry.field("最近更新"))
            if updated is None or updated < number:
                stale.append(entry.title)
    return stale


def check_project(project: Path, finishing: bool = False) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors must be fixed before writing; warnings are worth a look.

    With `finishing`, the write-back in progress is the one being closed, so it is not an
    error; instead the chapter's own write-back is checked for completeness.
    """
    errors: list[str] = []
    warnings: list[str] = []
    status_text = read(project, STATUS)
    if status_text is None:
        return [f"没有 {STATUS}：不是小说档案，或者还没建档"], []
    missing = [name for name in CORE_FILES if read(project, name) is None]
    if missing:
        errors.append(f"档案缺文件：{'、'.join(missing)}（用 novel.py init 补建，已有的不会被覆盖）")

    fields = status_fields(status_text)
    adopted = adopted_chapters(project)
    latest = adopted[-1] if adopted else 0

    claimed = chapter_number(fields.get("已采用到", ""))
    if adopted and claimed is None:
        errors.append(f"{STATUS} 写“已采用到：无”，{BODY_DIR}/ 里已经有 {len(adopted)} 章（最新第{latest}章）")
    elif claimed is not None and claimed != latest:
        errors.append(f"{STATUS} 写已采用到第{claimed}章，{BODY_DIR}/ 里最新是第{latest}章")
    gaps = [n for n in range(1, latest + 1) if n not in adopted]
    if gaps:
        errors.append(f"{BODY_DIR}/ 缺章：{'、'.join(f'第{n}章' for n in gaps)}")

    candidate = fields.get("当前唯一候选", "")
    if candidate and not is_none(candidate):
        path_text = candidate.split("（")[0].strip().strip("`")
        if not (project / path_text).is_file():
            errors.append(f"{STATUS} 里的当前唯一候选 {path_text} 不存在")

    in_progress = writeback_in_progress(status_text)
    if in_progress is not None and not finishing:
        changed, unchanged = writeback_changes(project, in_progress)
        errors.append(f"第{in_progress}章的回写停在“进行中”：和采用前的快照比，已经改过 "
                      f"{'、'.join(changed) or '无'}；还没动 {'、'.join(unchanged) or '无'}。"
                      "按写一章第九节补完，再跑 novel.py done")

    handover = named_section(status_text, "交接")
    if handover is None:
        errors.append(f"{STATUS} 没有“交接”一节：照模板补上")
    else:
        size = len("\n".join(handover))
        if size > HANDOVER_CAP:
            warnings.append(f"交接一节有 {size} 字，超过 {HANDOVER_CAP}：已写进设定、规则或大纲的删掉，过时的挪走")
        updated = handover_chapter(handover)
        if latest and in_progress is None and (updated is None or updated < latest):
            warnings.append(f"交接停在{f'第{updated}章后' if updated else '没更新过'}，正文已经到第{latest}章：先补上次对话里作者说过、还没写进档案的话")
        if finishing and in_progress and (updated is None or updated < in_progress):
            errors.append(f"交接的“更新于”还没到第{in_progress}章：把上次停在哪、作者这次说过的话、当前张力写进去")

    if finishing and in_progress:
        timeline_text = read(project, TIMELINE) or ""
        filled = any(re.match(rf"^\s*[-*]\s*第0*{in_progress}章", line) and "待填写" not in line
                     for line in timeline_text.splitlines())
        if not filled:
            errors.append(f"{TIMELINE} 里还没有第{in_progress}章")
        outline = chapter_outline(read(project, OUTLINE) or "", in_progress)
        if outline:
            entries = (parse_entries(read(project, CHARACTERS) or "", CHARACTERS)
                       + parse_entries(read(project, SETTINGS) or "", SETTINGS))
            index = NameIndex(entries)
            unknown = [name for name in split_names(field_value(outline[1], "出场"))
                       if len(name) >= MIN_NAME and not index.knows(name)]
            if unknown:
                errors.append(f"第{in_progress}章细纲列的出场 {'、'.join(unknown)} 还没有条目：按条目格式补进 "
                              f"{CHARACTERS} 或 {SETTINGS}（人物还要进 {CURRENT}），写别名")
        stale = chapter_mentions_stale(project, in_progress)
        if stale:
            warnings.append(f"第{in_progress}章里出现的 {'、'.join(stale)}，人物现状的“最近更新”还没到第{in_progress}章："
                            "他们这一章没变化就把最近更新改成这一章，有变化就补上")

    pending = project / PENDING_DIR
    if pending.is_dir():
        stale_drafts = []
        for path in sorted(pending.glob("*")):
            match = CHAPTER_FILE_RE.match(path.name)
            if path.is_file() and match and int(match.group(1)) <= latest:
                stale_drafts.append(path.name)
        if stale_drafts:
            warnings.append(f"{PENDING_DIR}/ 里还有已采用章节的稿子：{'、'.join(stale_drafts)}（作者在改旧章，还是采用时漏挪了）")

    outline_text = read(project, OUTLINE) or ""
    outlines = current_outlines(outline_text)
    outline_ids: dict[str, list[int]] = {}
    for number, title, lines in outlines:
        if not field_value(lines, "出场") or not field_value(lines, "伏笔"):
            errors.append(f"细纲「{title}」缺“出场”或“伏笔”一行（没有就写“无”）")
        for fid in set(FORESHADOW_ID_RE.findall("\n".join(lines))):
            outline_ids.setdefault(fid, []).append(number)

    foreshadow_text = read(project, FORESHADOW)
    if foreshadow_text is not None:
        entries = parse_entries(foreshadow_text, FORESHADOW)
        seen: dict[str, int] = {}
        for entry in entries:
            if FORESHADOW_ID_RE.fullmatch(entry.title):
                seen[entry.title] = seen.get(entry.title, 0) + 1
        duplicates = sorted(fid for fid, count in seen.items() if count > 1)
        if duplicates:
            errors.append(f"{FORESHADOW} 里编号重复：{'、'.join(duplicates)}")
        open_entries = [entry for entry in entries if entry.section != "已收的"]
        open_ids = {entry.title for entry in open_entries}
        closed_ids = {entry.title for entry in entries if entry.section == "已收的"}
        for fid, chapters in sorted(outline_ids.items()):
            where = "、".join(f"第{n}章" for n in sorted(chapters))
            if fid not in open_ids and fid not in closed_ids:
                errors.append(f"{fid} 在{where}细纲里出现，{FORESHADOW} 里没有")
            elif fid not in open_ids:
                warnings.append(f"{fid} 在{where}细纲里出现，记录里已经收掉了")
        if adopted:
            no_link = [entry.title for entry in open_entries if not field_value(entry.lines, "涉及")]
            if no_link:
                errors.append(f"没收的伏笔缺“涉及”一行：{'、'.join(no_link)}（资料包靠它找伏笔）")
            unfilled = [entry.title for entry in open_entries if "待填写" in entry.text]
            if unfilled:
                warnings.append(f"没收的伏笔里还有“待填写”：{'、'.join(unfilled)}")

    characters = parse_entries(read(project, CHARACTERS) or "", CHARACTERS)
    no_alias = [entry.title for entry in characters if not any(
        FIELD_RE.match(line) and FIELD_RE.match(line).group(1).strip() == "别名" for line in entry.lines)]
    if no_alias:
        errors.append(f"{CHARACTERS} 里缺“别名”一行：{'、'.join(no_alias)}（没有别名写“无”）")
    settings = [entry for entry in parse_entries(read(project, SETTINGS) or "", SETTINGS)
                if entry.section == "重要地点和物品"]
    no_alias = [entry.title for entry in settings if not any(
        FIELD_RE.match(line) and FIELD_RE.match(line).group(1).strip() == "别名" for line in entry.lines)]
    if no_alias:
        errors.append(f"{SETTINGS} 的重要地点和物品里缺“别名”一行：{'、'.join(no_alias)}")

    current_text = read(project, CURRENT)
    if current_text is not None:
        current = parse_entries(current_text, CURRENT)
        no_state = [entry.title for entry in current if not entry.field("状态")]
        if no_state:
            errors.append(f"{CURRENT} 里缺“状态”一行：{'、'.join(no_state)}")
        if adopted:
            tracked = {entry.title for entry in current}
            untracked = [entry.title for entry in characters if entry.title not in tracked]
            if untracked:
                warnings.append(f"{CHARACTERS} 里有、{CURRENT} 里没有：{'、'.join(untracked)}")
        index = NameIndex(characters + current)
        for number, title, lines in outlines:
            special = {index.canonical.get(name, name) for name in
                       split_names(re.sub(r"[（(][^）)]*[）)]", "", field_value(lines, "特殊出场")))}
            named = set(index.scan("\n".join(lines[1:])))
            for entry in current:
                state = entry.field("状态")
                if state[:2] not in ("死亡", "失踪") or entry.title not in named or entry.title in special:
                    continue
                message = (f"{entry.title} 在记录里是“{state}”，却出现在细纲「{title}」里：是回忆、假死这类有意安排，"
                           f"就在那章细纲加一行“- 特殊出场：{entry.title}（原因）”；不是就问作者")
                (errors if number == latest + 1 else warnings).append(message)

    for name, cap in SIZE_CAPS.items():
        text = read(project, name)
        if text is not None and len(text) > cap:
            warnings.append(f"{name} 有 {len(text)} 字，超过 {cap}：该归档或合并精简了（见 档案.md 的“每份文件多长”）")
    timeline_text = read(project, TIMELINE) or ""
    if len(re.findall(r"^\s*[-*]\s*第0*\d+章", timeline_text, flags=re.M)) > 60:
        warnings.append(f"{TIMELINE} 超过 60 章没归档：一卷写完要整段挪进卷总结")
    return errors, warnings
