FROM python:3.12-slim AS builder
WORKDIR /app/
COPY uv.lock .
COPY pyproject.toml .
RUN apt-get update && apt-get install -y \
     --no-install-recommends curl ca-certificates
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH=/root/.local/bin:$PATH
RUN uv sync --frozen

FROM python:3.12-slim
WORKDIR /app/
RUN apt-get update && apt-get install -y \
    python3-pip \
    libpango-1.0-0\
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libffi-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/.venv /app/.venv
COPY . .
ENV PATH=/app/.venv/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EXPOSE 8000