# PHASE 7: multi-stage build for the Cloud Run Class Aggregator push
# subscriber (src/eduagent/server.py). Multi-stage keeps the final image free
# of build tooling/pip cache; non-root user follows least-privilege the same
# way the rest of this project does (see design principle #5 in docs/eligibility_statement.md).

# ---- Builder: resolve + install Python dependencies only ----
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Final: copy only the installed packages + app source, run as non-root ----
FROM python:3.12-slim

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin eduagent

WORKDIR /app

COPY --from=builder --chown=eduagent:eduagent /root/.local /home/eduagent/.local
COPY --chown=eduagent:eduagent src/ ./src/
COPY --chown=eduagent:eduagent pyproject.toml ./



ENV PATH=/home/eduagent/.local/bin:$PATH \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER eduagent

# Cloud Run sets $PORT and expects the container to listen on it -- default
# to 8080 for local `docker run` without that env var set.
EXPOSE 8080
CMD ["sh", "-c", "uvicorn eduagent.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
