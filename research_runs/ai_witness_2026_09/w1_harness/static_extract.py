"""T0: common deterministic static extraction (method_contract.md).

* Changed functions: diff hunks mapped to enclosing Go functions / Java methods
  in both production versions.
* Changed symbols/paths -> normalized tokens (camelCase/snake split, lowercase).
* Supplied tests ranked by token overlap with the changed tokens; ties broken
  lexically by (path, name).
* Direct syntactic calls of the entry-point tests and changed functions, with
  source spans, and definition spans for callees defined in packet files.

This is lexical, not a sound call graph, and it supplies no obligation answers.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any

GO_FUNC = re.compile(r"^func\s+(?:\((?P<recv>[^)]*)\)\s*)?(?P<name>[A-Za-z_]\w*)\s*\(", re.M)
JAVA_METHOD = re.compile(
    r"^[ \t]*(?:(?:public|protected|private|static|final|synchronized|abstract|native)\s+)*"
    r"(?:<[^>]+>\s*)?[\w.\[\]<>,? ]+?\s+(?P<name>[A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:throws[\w.,\s]+)?\{",
    re.M,
)
CALL = re.compile(r"(?<![\w.])(?:(?P<recv>[A-Za-z_]\w*)\s*\.\s*)?(?P<name>[A-Za-z_]\w*)\s*\(")
KEYWORDS = {
    "if", "for", "switch", "return", "func", "go", "defer", "select", "case", "make", "len", "cap", "new",
    "append", "panic", "recover", "copy", "delete", "while", "catch", "synchronized", "super", "this", "throw",
    "int", "string", "byte", "error", "bool", "interface", "struct", "map", "chan", "else", "try", "assert",
}


@dataclass
class Func:
    path: str
    name: str
    qualname: str
    start: int  # 1-based inclusive
    end: int

    def span(self) -> str:
        return f"{self.path}:{self.start}-{self.end}"


def _block_end(lines: list[str], start_idx: int) -> int:
    """Index of the line closing the brace block opened at/after start_idx (lexical, skips strings/comments)."""
    depth = 0
    opened = False
    in_block_comment = False
    for i in range(start_idx, len(lines)):
        line = lines[i]
        j = 0
        in_str: str | None = None
        while j < len(line):
            ch = line[j]
            nxt = line[j + 1] if j + 1 < len(line) else ""
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    j += 1
            elif in_str:
                if ch == "\\" and in_str != "`":
                    j += 1
                elif ch == in_str:
                    in_str = None
            elif ch == "/" and nxt == "/":
                break
            elif ch == "/" and nxt == "*":
                in_block_comment = True
                j += 1
            elif ch in "\"'`":
                in_str = ch
            elif ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth == 0:
                    return i
            j += 1
    return len(lines) - 1


def functions(path: str, text: str, language: str) -> list[Func]:
    lines = text.split("\n")
    out: list[Func] = []
    pattern = GO_FUNC if language == "go" else JAVA_METHOD
    for m in pattern.finditer(text):
        name = m.group("name")
        if language == "java" and name in KEYWORDS:
            continue
        start_idx = text.count("\n", 0, m.start())
        if language == "go":
            # gofmt'd top-level declarations close with "}" in column 0; brace counting
            # would be fooled by `interface{}` / `struct{}` in signatures.
            end_idx = next((i for i in range(start_idx, len(lines)) if lines[i].rstrip() == "}" or
                            (i == start_idx and lines[i].rstrip().endswith("}") and not lines[i].rstrip().endswith("{}"))),
                           len(lines) - 1)
        else:
            end_idx = _block_end(lines, start_idx)
        qual = name
        if language == "go" and m.group("recv"):
            recv = m.group("recv").split()[-1].lstrip("*")
            qual = f"({recv}).{name}"
        out.append(Func(path, name, qual, start_idx + 1, end_idx + 1))
    return out


def unified_diff(path: str, old: str, new: str) -> str:
    return "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{path}", tofile=f"b/{path}", n=3))


def changed_line_numbers(old: str, new: str) -> tuple[set[int], set[int]]:
    """1-based changed lines in old and new (replace/delete/insert opcodes)."""
    sm = difflib.SequenceMatcher(a=old.split("\n"), b=new.split("\n"), autojunk=False)
    a_lines: set[int] = set()
    b_lines: set[int] = set()
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        a_lines.update(range(i1 + 1, i2 + 1) if i2 > i1 else {max(1, i1)})
        b_lines.update(range(j1 + 1, j2 + 1) if j2 > j1 else {max(1, j1)})
    return a_lines, b_lines


def tokens(text: str) -> set[str]:
    out: set[str] = set()
    for ident in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text):
        parts = re.findall(r"[A-Z]+(?=[A-Z][a-z]|\d|\b)|[A-Z]?[a-z]+|[A-Z]+|\d+", ident.replace("_", " "))
        for p in parts:
            p = p.lower()
            if len(p) >= 3 and p not in KEYWORDS:
                out.add(p)
    return out


def calls_in(func: Func, lines: list[str]) -> list[dict[str, Any]]:
    out = []
    seen = set()
    for ln in range(func.start, func.end + 1):
        text = lines[ln - 1]
        code = text.split("//", 1)[0]
        for m in CALL.finditer(code):
            name = m.group("name")
            if name in KEYWORDS or name == func.name and ln == func.start:
                continue
            key = (m.group("recv"), name, ln)
            if key in seen:
                continue
            seen.add(key)
            out.append({"callee": (m.group("recv") + "." if m.group("recv") else "") + name, "name": name,
                        "span": f"{func.path}:{ln}"})
    return out


def extract(language: str, production: dict[str, tuple[str, str]], tests: dict[str, str],
            helpers: dict[str, str], entry_points: list[str]) -> dict[str, Any]:
    """production: path -> (defective_text, repaired_text); tests: supplied test files; helpers: other packet files."""
    changed: list[dict[str, Any]] = []
    changed_tokens: set[str] = set()
    for path in sorted(production):
        old, new = production[path]
        a_lines, b_lines = changed_line_numbers(old, new)
        for version, text, touched in (("defective", old, a_lines), ("repaired", new, b_lines)):
            lines = text.split("\n")
            for f in functions(path, text, language):
                hit = sorted(l for l in touched if f.start <= l <= f.end)
                if hit:
                    changed.append({"version": version, "function": f.qualname, "span": f.span(),
                                    "changed_lines": hit})
                    changed_tokens |= tokens(f.qualname)
            for l in touched:
                if 1 <= l <= len(lines):
                    changed_tokens |= tokens(lines[l - 1])
        changed_tokens |= tokens(path.rsplit("/", 1)[-1].rsplit(".", 1)[0])
    ranking = []
    all_defs: dict[str, list[str]] = {}
    file_funcs: dict[str, list[Func]] = {}
    for path, text in sorted({**helpers, **tests, **{p: v[0] for p, v in production.items()}}.items()):
        fs = functions(path, text, language)
        file_funcs[path] = fs
        for f in fs:
            all_defs.setdefault(f.name, []).append(f.span())
    for path in sorted(tests):
        text = tests[path]
        lines = text.split("\n")
        for f in file_funcs[path]:
            is_test = f.name.startswith("Test") if language == "go" else f.name.startswith("test")
            if not is_test:
                continue
            body = "\n".join(lines[f.start - 1:f.end])
            overlap = sorted(tokens(body) & changed_tokens)
            ranking.append({"test": f.name, "path": path, "span": f.span(), "score": len(overlap),
                            "overlap_tokens": overlap[:30]})
    ranking.sort(key=lambda r: (-r["score"], r["path"], r["test"]))
    for i, r in enumerate(ranking, 1):
        r["rank"] = i
    def is_entry(path: str, name: str) -> bool:
        if language == "go":
            return name in entry_points
        cls = path.split("src/test/", 1)[-1][:-5].replace("/", ".")
        return f"{cls}#{name}" in entry_points

    entry_ranks = [{"entry_point": e, "rank": r["rank"], "score": r["score"], "span": r["span"]}
                   for e in entry_points for r in ranking if is_entry(r["path"], r["test"]) and
                   (r["test"] == e or e.endswith("#" + r["test"]))]
    direct_calls = []
    targets = [f for p in sorted(tests) for f in file_funcs[p] if is_entry(p, f.name)]
    for c in changed:
        path = c["span"].split(":")[0]
        if c["version"] == "defective":
            targets += [f for f in file_funcs.get(path, []) if f.qualname == c["function"]]
    all_text = {**helpers, **tests, **{p: v[0] for p, v in production.items()}}
    for f in targets:
        lines = all_text[f.path].split("\n")
        calls = calls_in(f, lines)
        for c in calls:
            c["definitions"] = all_defs.get(c["name"], [])[:5]
        direct_calls.append({"caller": f.qualname, "span": f.span(), "calls": calls})
    return {
        "tool": "w1-T0/1",
        "limits": "lexical extraction; not a sound whole-program call graph; no obligation answers",
        "changed_functions": changed,
        "changed_tokens": sorted(changed_tokens),
        "test_ranking": ranking[:40],
        "tests_ranked_total": len(ranking),
        "entry_points": entry_points,
        "entry_point_ranks": entry_ranks,
        "direct_calls": direct_calls,
    }
