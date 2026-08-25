#!/usr/bin/env python3
"""
T0 -- path-token relevance scalar (the Step-3 change-aware signal).

The mechanism (NEXT-STEPS Step 3): for each test execution, measure how much the
test's *identity* overlaps, in repo-path vocabulary, with the files the triggering
commit changed. Concretely:

    T0(test, cycle) = max over changed files f in that cycle of
                      cosine( tfidf(tokens(test_path)), tfidf(tokens(f)) )

graded in [0,1], varying per test *within* a cycle (every test in a cycle sees the
same changed-file set but has a different identity, so scores differ). A test whose
package/module/class tokens land on a changed path scores high; an untouched test
scores ~0.

Design decisions (documented on purpose -- this module is the shared relevance path
for both the research run and the demo, per ADR 0004; no notebook-only shortcuts):

  * Test identity = the test's FULL repo-relative path (from test_name_map.csv), e.g.
    ``modules/security/src/test/java/org/apache/airavata/security/userstore/JDBCUserStoreTest.java``.
    This shares the top-level module directory (``modules/security``) with the changed
    files -- module-level co-location is a legitimate, strong TCP relevance signal that
    a bare FQN (``org.apache...JDBCUserStoreTest``) cannot see. TF-IDF down-weights the
    structural boilerplate (``src``, ``java``, ``test``) automatically. (Confirmed with
    Khalil 2026-08-10; FQN is available as a robustness variant via ``identity="fqn"``.)

  * Tokenizer: split every string into alphanumeric sub-tokens AND camelCase pieces,
    lowercased. ``JDBCUserStoreTest.java`` -> {jdbc, user, store, test, java}. Path
    separators / dots / dashes are delimiters.

  * IDF corpus = the union of {all test-identity documents} and {all changed-file-path
    documents} in the dataset. This is an INPUT-ONLY transform: it uses no Verdict / no
    outcome, only the repo's path namespace, so it introduces no label leakage into the
    prequential evaluation. IDF here is a property of the codebase vocabulary (the
    ubiquitous structural tokens get near-zero weight; discriminative module/class tokens
    get high weight), which is exactly what a deployed system would also have.

Public surface
--------------
    tokenize(s) -> list[str]
    PathRelevanceScorer.fit(documents)          # label-free vectorizer over path vocab
        .score_one(test_identity, changed_files) -> float in [0,1]
        .score_tests({name: identity}, changed_files) -> {name: float}   # (repo,commit)->scores
    compute_t0_column(df, name_to_path, ...) -> np.ndarray aligned to df.index

The ``score_tests`` shape ((test identities, changed files) -> per-test scores) is the
demo/research contract from ADR 0004; ``compute_t0_column`` is the thin dataframe wrapper
the Step-3 experiment uses.
"""
from __future__ import annotations

import ast
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# alphanumeric run OR camelCase piece OR acronym-before-Word OR digit run
_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|[0-9]+")


def tokenize(s: str) -> list[str]:
    """Split a repo path / FQN into lowercased path + camelCase tokens.

    'modules/security/.../JDBCUserStoreTest.java'
        -> ['modules','security',...,'jdbc','user','store','test','java']
    Non-string / empty -> []. Path separators, dots, dashes act as delimiters because
    the token regex only matches alphanumeric runs.
    """
    if not isinstance(s, str) or not s:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(s)]


def parse_files_changed(cell) -> list[str]:
    """FilesChanged cell (a Python-literal list string, or NaN) -> list[str].

    Raises on a malformed non-empty string rather than silently returning [] -- a
    corrupt FilesChanged column is a data failure, not an empty change set.
    """
    if cell is None or (isinstance(cell, float) and np.isnan(cell)):
        return []
    if isinstance(cell, list):
        return [str(x) for x in cell]
    if not isinstance(cell, str):
        raise TypeError(f"FilesChanged cell is neither list/str/NaN: {type(cell)!r}")
    cell = cell.strip()
    if cell == "" or cell == "[]":
        return []
    val = ast.literal_eval(cell)  # raises on corruption -- intended
    if not isinstance(val, (list, tuple)):
        raise ValueError(f"FilesChanged did not parse to a list: {cell[:80]!r}")
    return [str(x) for x in val]


class PathRelevanceScorer:
    """TF-IDF path-token cosine scorer. Fit once on the repo's path vocabulary."""

    def __init__(self, vectorizer: TfidfVectorizer):
        self._vec = vectorizer  # fitted, norm='l2' -> cosine == dot product

    @classmethod
    def fit(cls, documents) -> "PathRelevanceScorer":
        docs = [d for d in documents if isinstance(d, str) and d]
        if not docs:
            raise ValueError("PathRelevanceScorer.fit got an empty corpus.")
        vec = TfidfVectorizer(tokenizer=tokenize, token_pattern=None,
                              lowercase=False, norm="l2")
        vec.fit(docs)
        if len(vec.vocabulary_) == 0:
            raise ValueError("PathRelevanceScorer produced an empty vocabulary.")
        return cls(vec)

    def score_one(self, test_identity: str, changed_files) -> float:
        """max cosine(test_identity, f) over changed files; 0.0 if none/no overlap."""
        files = [f for f in changed_files if isinstance(f, str) and f]
        if not test_identity or not files:
            return 0.0
        tv = self._vec.transform([test_identity])            # 1 x V (L2)
        fm = self._vec.transform(files)                      # F x V (L2)
        sims = (fm @ tv.T).toarray().ravel()                 # cosine == dot (both L2)
        if sims.size == 0:
            return 0.0
        return float(np.clip(sims.max(), 0.0, 1.0))

    def score_tests(self, name_to_identity: dict, changed_files) -> dict:
        """(test identities, changed files) -> {test name: max-cosine}. ADR-0004 shape."""
        files = [f for f in changed_files if isinstance(f, str) and f]
        if not files:
            return {name: 0.0 for name in name_to_identity}
        fm = self._vec.transform(files)                      # F x V (L2)
        names = list(name_to_identity)
        idents = [name_to_identity[n] for n in names]
        tm = self._vec.transform(idents)                     # T x V (L2)
        sims = (tm @ fm.T).toarray()                         # T x F cosine
        maxsim = np.clip(sims.max(axis=1), 0.0, 1.0)
        return {n: float(v) for n, v in zip(names, maxsim)}


def compute_t0_column(df, name_to_path, name_col="Name", cycle_col="Cycle",
                      files_col="FilesChanged", identity="path"):
    """Return a float ndarray of T0 aligned to df.index.

    name_to_path : {FQN -> full repo path} (and identity="path"), or the FQN itself is
    used directly when identity="fqn". Every df[name_col] value MUST be in name_to_path
    (path mode) -- an unmapped test is a name-join failure and raises (no silent 0).

    IDF corpus = unique test identities + unique changed-file paths across the whole df.
    Scores are computed per cycle via one T x F matmul (all tests in a cycle share the
    same changed-file set). Asserts FilesChanged is constant within a cycle.
    """
    if identity not in ("path", "fqn"):
        raise ValueError(f"identity must be 'path' or 'fqn', got {identity!r}")

    names = df[name_col].astype(str)
    if identity == "path":
        missing = sorted(set(names) - set(name_to_path))
        if missing:
            raise KeyError(f"{len(missing)} test name(s) missing from name map "
                           f"(name-join failure): {missing[:5]}")
        ident_of = {n: name_to_path[n] for n in names.unique()}
    else:
        ident_of = {n: n for n in names.unique()}

    # --- build the label-free IDF corpus: test identities + all changed files ---
    all_files = set()
    files_by_cycle = {}
    for cyc, g in df.groupby(cycle_col, sort=False):
        raw = g[files_col].unique()
        parsed = [parse_files_changed(r) for r in raw]
        # FilesChanged must be constant within a cycle (it is the commit's change set)
        norm = {tuple(sorted(p)) for p in parsed}
        if len(norm) > 1:
            raise ValueError(f"cycle {cyc}: FilesChanged not constant within cycle "
                             f"({len(norm)} distinct sets) -- schema/join bug")
        flist = parsed[0] if parsed else []
        files_by_cycle[cyc] = flist
        all_files.update(flist)

    corpus = list(ident_of.values()) + sorted(all_files)
    scorer = PathRelevanceScorer.fit(corpus)

    out = np.zeros(len(df), dtype=float)
    idx_of_label = {lbl: i for i, lbl in enumerate(df.index)}
    for cyc, g in df.groupby(cycle_col, sort=False):
        files = files_by_cycle[cyc]
        sub = {n: ident_of[n] for n in g[name_col].astype(str).unique()}
        scores = scorer.score_tests(sub, files)
        for lbl, nm in zip(g.index, g[name_col].astype(str)):
            out[idx_of_label[lbl]] = scores[nm]
    return out
