FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY src ./src
COPY scripts ./scripts
COPY data/templates ./data/templates
COPY README.md ./

RUN mkdir -p data/security_logs data/raw data/processed data/current data/source_cache data/prediction_logs data/active_draws/cache data/active_draws/logs data/active_draws/snapshots \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/streamlit_app.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true", "--browser.gatherUsageStats", "false"]
