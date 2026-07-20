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

# La interfaz de escucha es configurable porque los dos entornos la necesitan
# distinta, y no existe un valor que sirva para ambos:
#
#   Railway         -> red privada IPv6: hay que escuchar en ::
#   docker-compose  -> red IPv4: hay que escuchar en 0.0.0.0
#
# El valor por defecto es :: a proposito. Railway se despliega desde este
# Dockerfile sin nada mas, asi que el caso que no se puede configurar a mano
# es el que tiene que funcionar solo; docker-compose si puede fijar el suyo, y
# lo hace. Antes el defecto era 0.0.0.0 y los dos servicios quedaron caidos en
# produccion sin que nadie lo notara: la conexion agotaba el tiempo en vez de
# ser rechazada, asi que el error llegaba vacio.
# https://docs.railway.com/private-networking
ENV BIND_HOST=::
# El puerto sale de PORT si el entorno lo define -- Railway lo hace-- y si no
# del valor propio del servicio. Va dentro de `sh -c` a proposito: en forma
# exec la variable no se expande y uvicorn recibe la cadena literal "$PORT",
# que fue exactamente lo que dejo a los dos servicios en bucle de reinicio.
CMD ["sh", "-c", "uvicorn app.main:app --host \"$BIND_HOST\" --port \"${PORT:-8001}\""]
