FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN uv sync

CMD ["uv", "run", "python", "src/data_foundry/main.py"]
