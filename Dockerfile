# ── Stage 1: builder ─────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

COPY pyproject.toml ./

RUN pip install --no-cache-dir --prefix=/install .

COPY . .

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

COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY pyproject.toml ./

RUN mkdir -p outputs

EXPOSE 8000 8050

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "scripts/run_app.py"]
