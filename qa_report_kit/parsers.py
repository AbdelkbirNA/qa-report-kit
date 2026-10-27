"""Read test results from Robot Framework output.xml and JUnit XML into one shape."""
from dataclasses import dataclass, field
from datetime import datetime
import xml.etree.ElementTree as ET


@dataclass(frozen=True)
class TestResult:
    suite: str
    name: str
    status: str  # PASS | FAIL | SKIP
    duration_s: float
    message: str = ""
    tags: tuple = field(default_factory=tuple)

    @property
    def id(self):
        return f"{self.suite}::{self.name}"


def load(path):
    """Detect the format from the root element and parse it."""
    root = ET.parse(path).getroot()
    if root.tag == "robot":
        return _robot(root)
    if root.tag in ("testsuites", "testsuite"):
        return _junit(root)
    raise ValueError(f"{path}: unsupported root <{root.tag}>, expected <robot> or <testsuite(s)>")


def _robot_duration(status):
    # Robot 7 writes start + elapsed; Robot 6 and older write starttime + endtime.
    if status.get("elapsed") is not None:
        return float(status.get("elapsed"))
    start, end = status.get("starttime"), status.get("endtime")
    if start and end and start != "N/A":
        fmt = "%Y%m%d %H:%M:%S.%f"
        return (datetime.strptime(end, fmt) - datetime.strptime(start, fmt)).total_seconds()
    return 0.0


def _robot(root):
    results = []

    def walk(suite, path):
        name = suite.get("name", "")
        here = f"{path}.{name}" if path else name
        for test in suite.findall("test"):
            status = test.find("status")
            results.append(TestResult(
                suite=here,
                name=test.get("name", ""),
                status=status.get("status", "FAIL"),
                duration_s=_robot_duration(status),
                message=(status.text or "").strip(),
                tags=tuple(t.text for t in test.findall("tag") if t.text),
            ))
        for child in suite.findall("suite"):
            walk(child, here)

    for suite in root.findall("suite"):
        walk(suite, "")
    return results


def _junit(root):
    suites = [root] if root.tag == "testsuite" else root.iter("testsuite")
    results = []
    for suite in suites:
        for case in suite.findall("testcase"):
            failure = case.find("failure")
            if failure is None:
                failure = case.find("error")
            if failure is not None:
                status, message = "FAIL", (failure.get("message") or failure.text or "").strip()
            elif case.find("skipped") is not None:
                status, message = "SKIP", (case.find("skipped").get("message") or "").strip()
            else:
                status, message = "PASS", ""
            props = case.find("properties")
            tags = tuple(p.get("value", "") for p in props.findall("property")
                         if p.get("name") in ("tag", "requirement")) if props is not None else ()
            results.append(TestResult(
                suite=case.get("classname") or suite.get("name", ""),
                name=case.get("name", ""),
                status=status,
                duration_s=float(case.get("time") or 0),
                message=message,
                tags=tags,
            ))
    return results
