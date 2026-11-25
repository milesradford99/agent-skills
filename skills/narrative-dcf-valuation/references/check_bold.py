#!/usr/bin/env python3
"""检查（并可修复）Markdown 报告里不会被渲染成粗体的 **。

CommonMark 规定：收尾的 ** 如果紧跟在标点后面（如“。”“）”），后面必须是空白或标点；
开头的 ** 如果后面紧跟标点（如“（”“"”），前面必须是空白或标点。中文正文里
“……参数。**如果”这种写法因此不生效，读者会看到字面的 **。

用法：
  python3 check_bold.py 报告.md [更多.md]        # 只检查，有问题时退出码为 1
  python3 check_bold.py --fix 报告.md            # 把句末标点挪到 ** 外面
"""
import re
import sys
import unicodedata

RUN = re.compile(r"\*\*")


def _is_space(ch):
    return ch == "" or ch.isspace()


def _is_punct(ch):
    return ch != "" and unicodedata.category(ch)[0] in "PS"


def _left_flanking(before, after):
    if _is_space(after):
        return False
    return not _is_punct(after) or _is_space(before) or _is_punct(before)


def _right_flanking(before, after):
    if _is_space(before):
        return False
    return not _is_punct(before) or _is_space(after) or _is_punct(after)


def _pairs(line):
    """按出现顺序两两配对 **，跳过行内代码。"""
    code = [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`", line)]
    pos = [m.start() for m in RUN.finditer(line)
           if not any(a <= m.start() < b for a, b in code)]
    return list(zip(pos[0::2], pos[1::2]))


def problems(line):
    out = []
    for o, c in _pairs(line):
        ob, oa = line[o - 1] if o else "", line[o + 2] if o + 2 < len(line) else ""
        cb, ca = line[c - 1] if c else "", line[c + 2] if c + 2 < len(line) else ""
        if not _left_flanking(ob, oa) or not _right_flanking(cb, ca):
            out.append((o, c))
    return out


def fix_line(line):
    # 从后往前改，避免下标错位
    for o, c in reversed(_pairs(line)):
        ob, oa = line[o - 1] if o else "", line[o + 2] if o + 2 < len(line) else ""
        cb, ca = line[c - 1] if c else "", line[c + 2] if c + 2 < len(line) else ""
        if not _right_flanking(cb, ca):
            k = c
            while k > o + 2 and _is_punct(line[k - 1]):
                k -= 1
            line = line[:k] + "**" + line[k:c] + line[c + 2:]
        if not _left_flanking(ob, oa):
            k = o + 2
            while k < len(line) and _is_punct(line[k]) and line[k] != "*":
                k += 1
            line = line[:o] + line[o + 2:k] + "**" + line[k:]
    return line


def main(argv):
    fix = "--fix" in argv
    files = [a for a in argv if a != "--fix"]
    if not files:
        print(__doc__)
        return 2
    bad = 0
    for f in files:
        text = open(f, encoding="utf-8").read()
        lines = text.split("\n")
        if fix:
            new = [fix_line(l) for l in lines]
            if new != lines:
                open(f, "w", encoding="utf-8").write("\n".join(new))
            lines = new
        for i, l in enumerate(lines, 1):
            for o, c in problems(l):
                bad += 1
                print(f"{f}:{i}: 粗体不会生效：{l[max(0, o - 6):c + 8]}")
    if bad:
        print(f"共 {bad} 处。把句末标点移到 ** 外面（**……参数**。），或运行 --fix。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
