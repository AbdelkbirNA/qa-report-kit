"""qa-report: turn Robot Framework / JUnit results into a quality report and a CI gate.

    python -m qa_report_kit RUN.xml [RUN2.xml ...] [--requirements reqs.csv]
                            [--html report.html] [--md report.md] [--min-pass-rate 95]

Several runs of the same suite enable flaky-test detection; the last run is the one reported.
Exit code 1 when the pass rate is below --min-pass-rate or a requirement is failing or uncovered
(with --strict-trace).
"""
import argparse
import sys

from . import metrics, parsers, report


def main(argv=None):
    p = argparse.ArgumentParser(prog="qa-report", description=__doc__.splitlines()[0])
    p.add_argument("runs", nargs="+", help="Robot output.xml or JUnit XML, oldest first")
    p.add_argument("--requirements", help="CSV: requirement,test (glob or tag:<TAG>)")
    p.add_argument("--html")
    p.add_argument("--md")
    p.add_argument("--min-pass-rate", type=float, default=0.0)
    p.add_argument("--strict-trace", action="store_true")
    a = p.parse_args(argv)

    runs = [parsers.load(path) for path in a.runs]
    latest = runs[-1]
    s = metrics.summary(latest)
    clusters = metrics.cluster_failures(latest)
    flaky = metrics.flaky(runs) if len(runs) > 1 else {}
    trace = metrics.traceability(latest, metrics.load_requirements(a.requirements)) if a.requirements else {}

    md = report.markdown(s, clusters, flaky, trace)
    if a.md:
        open(a.md, "w", encoding="utf-8").write(md)
    if a.html:
        open(a.html, "w", encoding="utf-8").write(report.html(s, clusters, flaky, trace))
    if not (a.md or a.html):
        sys.stdout.write(md)

    failed_gate = s["pass_rate"] < a.min_pass_rate
    if a.strict_trace:
        failed_gate |= any(v["state"] != "COVERED" for v in trace.values())
    return 1 if failed_gate else 0


if __name__ == "__main__":
    sys.exit(main())
