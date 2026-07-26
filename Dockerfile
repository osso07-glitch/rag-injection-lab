FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RAG_LAB_DATA_DIR=/app/data \
    RAG_LAB_META_DIR=/app/meta \
    RAG_LAB_HOST=0.0.0.0 \
    RAG_LAB_PORT=8505

COPY pyproject.toml README.md ./
COPY src ./src
COPY app ./app
COPY data/kb ./data/kb

RUN pip install --upgrade pip && pip install .

EXPOSE 8505

# Bind 0.0.0.0 inside the container so published ports work.
# Prefer keeping the host publish on 127.0.0.1 (see docker-compose).
CMD ["streamlit", "run", "app/Home.py", "--server.address", "0.0.0.0", "--server.port", "8505", "--browser.gatherUsageStats", "false"]
