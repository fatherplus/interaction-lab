FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    IL_HOST=0.0.0.0 \
    IL_PORT=8900 \
    IL_DB_PATH=/data/telemetry.sqlite

WORKDIR /app

# Only the sources the build actually needs; no third-party packages required.
COPY data/patterns.json ./data/patterns.json
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY cli/ ./cli/
COPY skill/ ./skill/
COPY server/ ./server/
COPY build.py ./build.py

RUN chmod +x cli/ilab \
    && python3 build.py \
    && useradd --system --uid 10001 --home /app ilab \
    && mkdir -p /data \
    && chown -R ilab:ilab /app /data

USER ilab

VOLUME ["/data"]
EXPOSE 8900

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python3 -c "import os,urllib.request,sys; u=f\"http://127.0.0.1:{os.environ.get('IL_PORT','8900')}/api/health\"; sys.exit(0 if urllib.request.urlopen(u, timeout=3).status==200 else 1)"

CMD ["python3", "server/app.py"]
