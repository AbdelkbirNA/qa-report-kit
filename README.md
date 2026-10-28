# qa-report-kit

Turns test results into a quality report and a CI quality gate.

- Reads **Robot Framework `output.xml`** and **JUnit XML** (pytest, Playwright, Cypress, Jenkins).
- **Summary**: pass rate, failed and skipped tests, total duration, slowest tests.
- **Failures grouped by cause**: messages are normalised (numbers, quoted values, addresses) so one root cause shows up once.
- **Flaky tests**: pass several runs of the same suite; tests whose status changes are listed.
- **Requirement traceability**: a CSV maps each requirement to tests (glob on the name, or `tag:<TAG>`); each requirement is COVERED, FAILING or UNCOVERED.
- **Outputs**: Markdown (written to the GitHub Actions job summary) and a single-file HTML dashboard.
- **Gate**: exit code 1 below `--min-pass-rate`, or with `--strict-trace` when a requirement is not covered.

No dependency outside the Python standard library.

```bash
python -m qa_report_kit tests/fixtures/qa_pipeline_output.xml \
  --requirements examples/requirements.csv --html report.html --md report.md --min-pass-rate 95

# flaky detection: several runs, oldest first
python -m qa_report_kit run1.xml run2.xml run3.xml --md report.md
```

The sample run in `tests/fixtures/` is a real execution of
[QA-Pipeline](https://github.com/AbdelkbirNA/QA-Pipeline) (Robot Framework, 61 API and UI tests).
`REQ-PAY-01` in the example matrix is deliberately uncovered, to show the gap in the report.

## Docker and Kubernetes

```bash
docker build -t qa-report-kit:ci .
docker run --rm -v "$PWD/tests/fixtures:/r:ro" qa-report-kit:ci /r/qa_pipeline_output.xml --min-pass-rate 95
```

`k8s/job.yaml` runs the gate as a Kubernetes Job: the results are mounted from a ConfigMap and the
Job fails when the gate fails. CI builds the image, loads it into a kind cluster and waits for the Job.

## Tests

```bash
pip install pytest && pytest -q
```

CI runs the suite and publishes the sample report as an artifact.

Built with Claude Code.
