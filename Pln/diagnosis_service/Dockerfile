FROM python:3.12-slim

WORKDIR /service

# Dependencias del sistema para compilar python-Levenshtein
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código y los artefactos (modelos + léxico)
COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8001

# Healthcheck que usa el endpoint /health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
