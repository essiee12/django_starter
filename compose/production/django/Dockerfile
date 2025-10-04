FROM python:3.13-bookworm-slim AS base
FROM base AS builder

COPY --from=ghcr.io/astral-sh/uv:0.8.10 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

ENV PYTHONUNBUFFERED 1

COPY uv.lock /uv.lock
COPY pyproject.toml /pyproject.toml
RUN uv sync --frozen --no-install-project

COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r//' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/production/django/start /start
RUN sed -i 's/\r//' /start
RUN chmod +x /start

COPY ./compose/production/django/celery_start /celery_start
RUN sed -i 's/\r//' /celery_start
RUN chmod +x /celery_start

COPY ./compose/production/django/celery_beat /celery_beat
RUN sed -i 's/\r//' /celery_beat
RUN chmod +x /celery_beat

RUN mkdir /djtemp

COPY backend /app

WORKDIR /app

ENTRYPOINT ["/entrypoint"]