# ── Stage 1: builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY . .

RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: runtime ────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

WORKDIR /app

COPY --from=builder /build/app/ ./app/
COPY --from=builder /build/scripts/ ./scripts/
COPY --from=builder /build/data/ ./data/
COPY --from=builder /build/profiles/ ./profiles/
COPY --from=builder /build/config/ ./config/
COPY --from=builder /build/pyproject.toml ./

RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser \
    && mkdir -p outputs \
    && chown -R appuser:appuser /app outputs

USER appuser

ENV HOST=0.0.0.0
ENV GRADIO_SERVER_NAME=0.0.0.0

EXPOSE 8000 8050

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "scripts/run_app.py"]
