FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /project

ENV UV_PROJECT_ENVIRONMENT=/project/.venv
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project

RUN uv run python -m ipykernel install \
    --sys-prefix \
    --name pydev \
    --display-name "Python (Docker)"