#!/usr/bin/env python3
"""
Rung-1 precise name relevance (the higher-precision successor to T0).

The hbase viability gate showed T0's TF-IDF cosine fires for ~97.5% of failing tests
(ubiquitous structural tokens) while true relevance is only 6-31% -- so T0 is weak
because it is *imprecise*, not because relevance is absent. These two signals trade
recall for precision:

  exact_target_hit(test, changed_files) -> {0,1}
      1 iff the test's TARGET class (TestFoo->Foo, FooTest->Foo) is literally one of
      the changed .java files. Near-certain relevance; fires ~6% on hbase.
  package_hit(test, changed_files) -> {0,1}
      1 iff the test's package is among the changed files' packages. Looser; ~31%.

Both are label-free and vary per test within a cycle, so they plug into the step3
harness exactly like T0 (compare HIST vs HIST + these features).
"""
from __future__ import annotations

import ast

import numpy as np

from lrts_adapter import path_to_fqn  # reuse the adapter's path->FQN convention

_AFFIX_SUFFIXES = ("Test", "Tests", "TestCase", "IT", "ITCase")


def _simple_and_pkg(fqn: str) -> tuple[str, str]:
    parts = str(fqn).split(".")
    return parts[-1], ".".join(parts[:-1])


def target_class(test_simple: str) -> str:
    """Test class simple name -> the production class it targets.
    TestFoo/FooTest/FooIT -> Foo; a name with no test affix maps to itself."""
    s = test_simple
    for suf in _AFFIX_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            return s[:-len(suf)]
    if s.startswith("Test") and len(s) > len("Test"):
        return s[len("Test"):]
    return s


def _parse_files(cell) -> list[str]:
    if isinstance(cell, list):
        return [str(x) for x in cell]
    if not isinstance(cell, str) or not cell.strip():
        return []
    val = ast.literal_eval(cell)
    return [str(x) for x in val] if isinstance(val, (list, tuple)) else []


def _changed_classes_and_pkgs(changed_files) -> tuple[set, set]:
    classes, pkgs = set(), set()
    for f in changed_files:
        if not str(f).endswith(".java"):
            continue
        cls, pkg = _simple_and_pkg(path_to_fqn(f))
        classes.add(cls)
        if pkg:
            pkgs.add(pkg)
    return classes, pkgs


def exact_target_hit(test_fqn: str, changed_files) -> int:
    """1 iff the test's target class is one of the changed .java files."""
    simple, _ = _simple_and_pkg(test_fqn)
    tgt = target_class(simple)
    classes, _ = _changed_classes_and_pkgs(changed_files)
    return int(tgt in classes)


def package_hit(test_fqn: str, changed_files) -> int:
    """1 iff the test's package is among the changed files' packages."""
    _, pkg = _simple_and_pkg(test_fqn)
    _, pkgs = _changed_classes_and_pkgs(changed_files)
    return int(bool(pkg) and pkg in pkgs)


def compute_precise_columns(df, name_col: str = "Name", cycle_col: str = "Cycle",
                            files_col: str = "FilesChanged"):
    """Return (exact_target_hit, package_hit) int ndarrays aligned to df.index.

    FilesChanged is constant within a cycle, so parse + derive changed classes/pkgs
    once per cycle and reuse for every test row in it.
    """
    exact = np.zeros(len(df), dtype=int)
    pkg = np.zeros(len(df), dtype=int)
    pos = {lbl: i for i, lbl in enumerate(df.index)}
    for _cyc, g in df.groupby(cycle_col, sort=False):
        files = _parse_files(g[files_col].iloc[0])
        classes, pkgs = _changed_classes_and_pkgs(files)
        for lbl, name in zip(g.index, g[name_col].astype(str)):
            simple, tpkg = _simple_and_pkg(name)
            exact[pos[lbl]] = int(target_class(simple) in classes)
            pkg[pos[lbl]] = int(bool(tpkg) and tpkg in pkgs)
    return exact, pkg
