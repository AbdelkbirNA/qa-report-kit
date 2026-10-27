from pathlib import Path

import pytest

from qa_report_kit import metrics, parsers, report
from qa_report_kit.__main__ import main

FIX = Path(__file__).parent / "fixtures"
ROBOT = FIX / "qa_pipeline_output.xml"  # real run of github.com/AbdelkbirNA/QA-Pipeline


def junit(tmp_path, name, cases):
    body = "".join(cases)
    p = tmp_path / name
    p.write_text(f'<testsuite name="checkout">{body}</testsuite>', encoding="utf-8")
    return p


PASS = '<testcase classname="checkout" name="{n}" time="0.5"/>'
FAIL = ('<testcase classname="checkout" name="{n}" time="1.2">'
        '<failure message="{m}"/></testcase>')


def test_robot_output_of_qa_pipeline_is_read():
    results = parsers.load(ROBOT)
    s = metrics.summary(results)
    assert s["total"] == 61
    assert s["pass"] == 61 and s["fail"] == 0
    assert s["pass_rate"] == 100.0
    assert all(r.suite.startswith("QA-Pipeline") for r in results)


def test_unknown_format_is_rejected(tmp_path):
    p = tmp_path / "x.xml"
    p.write_text("<html/>")
    with pytest.raises(ValueError, match="unsupported root"):
        parsers.load(p)


def test_junit_statuses_and_pass_rate(tmp_path):
    p = junit(tmp_path, "r.xml", [
        PASS.format(n="pay by card"),
        FAIL.format(n="pay by voucher", m="Expected 200 but got 500"),
        '<testcase classname="checkout" name="pay later" time="0"><skipped/></testcase>',
    ])
    s = metrics.summary(parsers.load(p))
    assert (s["pass"], s["fail"], s["skip"]) == (1, 1, 1)
    assert s["pass_rate"] == 50.0  # skipped tests do not count


def test_failures_with_same_cause_are_grouped(tmp_path):
    p = junit(tmp_path, "r.xml", [
        FAIL.format(n="a", m="Expected 200 but got 500 for id 12"),
        FAIL.format(n="b", m="Expected 200 but got 500 for id 97"),
        FAIL.format(n="c", m="Element 'css=#pay' not visible after 5s"),
    ])
    clusters = metrics.cluster_failures(parsers.load(p))
    assert [len(rs) for _, rs in clusters] == [2, 1]
    assert clusters[0][0] == "Expected <n> but got <n> for id <n>"


def test_flaky_tests_are_detected_across_runs(tmp_path):
    run1 = junit(tmp_path, "1.xml", [PASS.format(n="login"), PASS.format(n="logout")])
    run2 = junit(tmp_path, "2.xml", [FAIL.format(n="login", m="timeout"), PASS.format(n="logout")])
    flaky = metrics.flaky([parsers.load(run1), parsers.load(run2)])
    assert flaky == {"checkout::login": ["PASS", "FAIL"]}


def test_traceability_states(tmp_path):
    reqs = tmp_path / "reqs.csv"
    reqs.write_text("requirement,test\nREQ-1,pay by *\nREQ-2,refund\nREQ-3,tag:smoke\n")
    p = junit(tmp_path, "r.xml", [
        PASS.format(n="pay by card"),
        FAIL.format(n="pay by voucher", m="boom"),
        '<testcase classname="checkout" name="health" time="0.1"><properties>'
        '<property name="tag" value="smoke"/></properties></testcase>',
    ])
    trace = metrics.traceability(parsers.load(p), metrics.load_requirements(reqs))
    assert trace["REQ-1"]["state"] == "FAILING"
    assert trace["REQ-2"]["state"] == "UNCOVERED"
    assert trace["REQ-3"] == {"state": "COVERED", "tests": ["health"]}


def test_html_escapes_untrusted_text(tmp_path):
    p = junit(tmp_path, "r.xml", [FAIL.format(n="xss", m="&lt;script&gt;alert(1)&lt;/script&gt;")])
    results = parsers.load(p)
    out = report.html(metrics.summary(results), metrics.cluster_failures(results), {}, {})
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_cli_quality_gate(tmp_path):
    p = junit(tmp_path, "r.xml", [PASS.format(n="a"), FAIL.format(n="b", m="x")])
    html_out = tmp_path / "report.html"
    assert main([str(p), "--html", str(html_out), "--min-pass-rate", "40"]) == 0
    assert main([str(p), "--min-pass-rate", "90"]) == 1
    assert "Quality report" in html_out.read_text()
