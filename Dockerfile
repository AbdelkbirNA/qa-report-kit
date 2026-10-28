FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY qa_report_kit ./qa_report_kit
RUN pip install --no-cache-dir . && useradd --uid 10001 qa
USER qa
ENTRYPOINT ["qa-report"]
