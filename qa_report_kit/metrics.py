"""Quality metrics computed from one or several test runs."""
from collections import defaultdict
import csv
import fnmatch
import re


def summary(results, slowest=5):
    total = len(results)
    counts = {s: sum(r.status == s for r in results) for s in ("PASS", "FAIL", "SKIP")}
    executed = counts["PASS"] + counts["FAIL"]
    return {
        "total": total,
        **{k.lower(): v for k, v in counts.items()},
        "pass_rate": round(100 * counts["PASS"] / executed, 1) if executed else 0.0,
        "duration_s": round(sum(r.duration_s for r in results), 2),
        "slowest": sorted(results, key=lambda r: r.duration_s, reverse=True)[:slowest],
    }


def flaky(runs):
    """Tests whose status changed between runs (PASS in one, FAIL in another)."""
    seen = defaultdict(list)
    for run in runs:
        for r in run:
            if r.status != "SKIP":
                seen[r.id].append(r.status)
    return {tid: statuses for tid, statuses in seen.items() if len(set(statuses)) > 1}


_VOLATILE = [
    (re.compile(r"'[^']*'|\"[^\"]*\""), "<str>"),
    (re.compile(r"0x[0-9a-fA-F]+"), "<hex>"),
    (re.compile(r"\b\d+(\.\d+)?\b"), "<n>"),
]


def signature(message):
    """Strip values that change between runs so identical causes group together."""
    sig = message.splitlines()[0] if message else "(no message)"
    for pattern, repl in _VOLATILE:
        sig = pattern.sub(repl, sig)
    return sig.strip()[:160]


def cluster_failures(results):
    groups = defaultdict(list)
    for r in results:
        if r.status == "FAIL":
            groups[signature(r.message)].append(r)
    return sorted(groups.items(), key=lambda kv: len(kv[1]), reverse=True)


def load_requirements(path):
    """CSV with columns requirement,test  ('test' is a glob on the test name, or tag:<TAG>)."""
    reqs = defaultdict(list)
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            reqs[row["requirement"].strip()].append(row["test"].strip())
    return dict(reqs)


def traceability(results, requirements):
    """For each requirement: which tests cover it and whether they all pass."""
    matrix = {}
    for req, selectors in requirements.items():
        covered = [
            r for r in results
            for sel in selectors
            if (sel.startswith("tag:") and sel[4:] in r.tags) or fnmatch.fnmatch(r.name, sel)
        ]
        if not covered:
            state = "UNCOVERED"
        elif any(r.status == "FAIL" for r in covered):
            state = "FAILING"
        else:
            state = "COVERED"
        matrix[req] = {"state": state, "tests": sorted({r.name for r in covered})}
    return matrix
