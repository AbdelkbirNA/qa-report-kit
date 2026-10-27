"""Render the metrics as Markdown (for CI summaries) and a single-file HTML dashboard."""
from html import escape


def markdown(s, clusters, flaky, trace):
    lines = [
        "# Quality report",
        "",
        f"**{s['pass_rate']} %** pass rate · {s['pass']} passed · {s['fail']} failed · "
        f"{s['skip']} skipped · {s['total']} tests · {s['duration_s']} s",
        "",
    ]
    if clusters:
        lines += ["## Failures grouped by cause", "", "| Tests | Cause |", "|---|---|"]
        lines += [f"| {len(rs)} | `{sig}` |" for sig, rs in clusters]
        lines.append("")
    if flaky:
        lines += ["## Flaky tests", "", "| Test | Statuses across runs |", "|---|---|"]
        lines += [f"| {tid} | {' → '.join(st)} |" for tid, st in sorted(flaky.items())]
        lines.append("")
    if trace:
        lines += ["## Requirement traceability", "", "| Requirement | State | Tests |", "|---|---|---|"]
        lines += [f"| {req} | {v['state']} | {', '.join(v['tests']) or '—'} |" for req, v in trace.items()]
        lines.append("")
    lines += ["## Slowest tests", "", "| Test | Seconds |", "|---|---|"]
    lines += [f"| {r.name} | {r.duration_s:.2f} |" for r in s["slowest"]]
    return "\n".join(lines) + "\n"


_CSS = """
body{font:14px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:960px;padding:0 1rem;color:#1d2433}
h1{margin:0 0 .25rem}.kpis{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0 2rem}
.kpi{border:1px solid #d8dde6;border-radius:6px;padding:.75rem 1rem;min-width:120px}
.kpi b{display:block;font-size:1.6rem}table{border-collapse:collapse;width:100%;margin-bottom:2rem}
th,td{border-bottom:1px solid #e3e7ee;padding:.4rem .5rem;text-align:left;vertical-align:top}
code{font-size:12px}.FAILING,.FAIL{color:#b42318}.COVERED,.PASS{color:#067647}.UNCOVERED{color:#b54708}
"""


def _table(head, rows):
    th = "".join(f"<th>{escape(h)}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


def html(s, clusters, flaky, trace, title="Quality report"):
    kpis = [("Pass rate", f"{s['pass_rate']} %"), ("Passed", s["pass"]), ("Failed", s["fail"]),
            ("Skipped", s["skip"]), ("Duration", f"{s['duration_s']} s")]
    parts = [f"<h1>{escape(title)}</h1>", '<div class="kpis">']
    parts += [f'<div class="kpi"><b>{escape(str(v))}</b>{escape(k)}</div>' for k, v in kpis]
    parts.append("</div>")
    if clusters:
        parts.append("<h2>Failures grouped by cause</h2>")
        parts.append(_table(["Tests", "Cause", "Examples"], [
            (len(rs), f"<code>{escape(sig)}</code>", escape(", ".join(r.name for r in rs[:3])))
            for sig, rs in clusters]))
    if flaky:
        parts.append("<h2>Flaky tests</h2>")
        parts.append(_table(["Test", "Statuses across runs"],
                            [(escape(t), escape(" → ".join(st))) for t, st in sorted(flaky.items())]))
    if trace:
        parts.append("<h2>Requirement traceability</h2>")
        parts.append(_table(["Requirement", "State", "Tests"], [
            (escape(req), f'<span class="{v["state"]}">{v["state"]}</span>', escape(", ".join(v["tests"]) or "—"))
            for req, v in trace.items()]))
    parts.append("<h2>Slowest tests</h2>")
    parts.append(_table(["Test", "Suite", "Seconds"],
                        [(escape(r.name), escape(r.suite), f"{r.duration_s:.2f}") for r in s["slowest"]]))
    return (f"<!doctype html><html lang=\"en\"><meta charset=\"utf-8\"><title>{escape(title)}</title>"
            f"<style>{_CSS}</style><body>{''.join(parts)}</body></html>\n")
