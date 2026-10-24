#!/usr/bin/env python3
"""Validate every skill in this repo against the Agent Skills format.

Standard library only, so CI and contributors need nothing installed.

Usage:
    python3 scripts/validate_skills.py [REPO_ROOT]

Exits 0 when everything passes, 1 when any check fails.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
NAME_MAX = 64
DESCRIPTION_MAX = 1024
RESERVED_WORDS = ("anthropic", "claude")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    """Return (fields, body) for a file starting with a '---' block, else None.

    Supports the subset skills use: one `key: value` per line, values
    optionally wrapped in single or double quotes.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    body = "\n".join(lines[end + 1 :])
    return fields, body


def check_skill(skill_dir: Path) -> list[str]:
    """Return a list of problems for one skill directory (empty means valid)."""
    problems: list[str] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return [f"{skill_dir}: missing SKILL.md"]

    parsed = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if parsed is None:
        return [f"{skill_md}: must start with a '---' frontmatter block"]
    fields, body = parsed

    name = fields.get("name", "")
    if not name:
        problems.append(f"{skill_md}: frontmatter needs 'name'")
    else:
        if not NAME_RE.match(name):
            problems.append(f"{skill_md}: name '{name}' must be lowercase letters, digits and single hyphens")
        if len(name) > NAME_MAX:
            problems.append(f"{skill_md}: name is longer than {NAME_MAX} characters")
        if any(word in name for word in RESERVED_WORDS):
            problems.append(f"{skill_md}: name must not contain {' or '.join(RESERVED_WORDS)}")
        if name != skill_dir.name:
            problems.append(f"{skill_md}: name '{name}' must match its folder '{skill_dir.name}'")

    description = fields.get("description", "")
    if not description:
        problems.append(f"{skill_md}: frontmatter needs 'description'")
    else:
        if len(description) > DESCRIPTION_MAX:
            problems.append(f"{skill_md}: description is {len(description)} characters (max {DESCRIPTION_MAX})")
        if "<" in description or ">" in description:
            problems.append(f"{skill_md}: description must not contain angle brackets")

    if not body.strip():
        problems.append(f"{skill_md}: has no instructions after the frontmatter")
    return problems


def check_marketplace(root: Path, skill_dirs: list[Path]) -> list[str]:
    """Check the plugin marketplace lists every skill once and points at real folders."""
    path = root / ".claude-plugin" / "marketplace.json"
    if not path.is_file():
        return []  # optional for repos that don't ship a marketplace
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        return [f"{path}: invalid JSON ({err})"]

    problems: list[str] = []
    listed: list[str] = []
    for i, plugin in enumerate(data.get("plugins", [])):
        for entry in plugin.get("skills", []):
            target = (root / entry).resolve()
            if not (target / "SKILL.md").is_file():
                problems.append(f"{path}: plugins[{i}] lists '{entry}', which has no SKILL.md")
            listed.append(target.name)
    for skill_dir in skill_dirs:
        if listed.count(skill_dir.name) != 1:
            problems.append(f"{path}: skill '{skill_dir.name}' must be listed exactly once (found {listed.count(skill_dir.name)})")
    return problems


def validate_repo(root: Path) -> list[str]:
    skills_root = root / "skills"
    if not skills_root.is_dir():
        return [f"{root}: no skills/ folder"]
    skill_dirs = sorted(p for p in skills_root.iterdir() if p.is_dir())
    if not skill_dirs:
        return [f"{skills_root}: no skills found"]
    problems: list[str] = []
    for skill_dir in skill_dirs:
        problems.extend(check_skill(skill_dir))
    problems.extend(check_marketplace(root, skill_dirs))
    return problems


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path(__file__).resolve().parent.parent
    problems = validate_repo(root)
    for problem in problems:
        print(f"FAIL {problem}")
    if problems:
        print(f"{len(problems)} problem(s) found")
        return 1
    count = len([p for p in (root / "skills").iterdir() if p.is_dir()])
    print(f"OK {count} skill(s) valid")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
