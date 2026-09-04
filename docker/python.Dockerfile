FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN pip install --no-cache-dir uv==0.8.11

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

COPY alembic.ini ./
COPY migrations ./migrations
COPY apps ./apps
COPY packages ./packages

RUN useradd --create-home --uid 10001 alphadesk && chown -R alphadesk:alphadesk /app
USER alphadesk

ENV PATH="/app/.venv/bin:$PATH"

