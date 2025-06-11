FROM ghcr.io/astral-sh/uv:python3.13-bookworm

ADD . /app
WORKDIR /app

RUN uv sync --locked \
    && uv run playwright install --with-deps webkit

CMD ["uv", "run", "celery", "--app=tasks", "worker", "--loglevel=INFO"]
