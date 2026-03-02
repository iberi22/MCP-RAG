FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy source
COPY cerebro_python /app/cerebro_python
COPY pyproject.toml /app/pyproject.toml
COPY README.md /app/README.md

# Persist the database in a named volume
VOLUME ["/app/data"]

ENV PYTHONUNBUFFERED=1
ENV RAG_DB_PATH=/app/data/cerebro_rag.db

# MiniMax — set via docker-compose env_file or -e flags
ENV MINIMAX_MODEL=MiniMax-M2.5-highspeed

# Default: run as interactive CLI (rag-chat)
# Override with: docker run ... python -m cerebro_python rag-ask --question "..."
CMD ["python", "-m", "cerebro_python", "mcp"]
