FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (layer caching)
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir .

# Create non-root user for security
RUN addgroup --system --gid 1001 app && \
    adduser --system --uid 1001 --ingroup app --no-create-home app && \
    mkdir -p /data && chown app:app /data

USER app

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
