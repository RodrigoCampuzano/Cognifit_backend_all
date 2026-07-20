FROM python:3.12-slim

WORKDIR /service

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY data/ ./data/

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8002/health').raise_for_status()"

# La interfaz de escucha es configurable porque los dos entornos la necesitan
# distinta, y no hay un valor que sirva para ambos:
#
#   docker-compose  -> red IPv4: hay que escuchar en 0.0.0.0 (valor por defecto)
#   Railway         -> red privada IPv6: hay que escuchar en ::
#
# Enlazar solo a IPv6 deja el servicio inalcanzable desde una red IPv4, y al
# reves tambien. Ese era el sintoma en produccion: el nombre resolvia pero
# nadie respondia, dando ConnectTimeout con mensaje vacio en vez de
# "connection refused".
#
# En Railway hay que definir BIND_HOST=:: en las variables del servicio.
# https://docs.railway.com/private-networking
ENV BIND_HOST=0.0.0.0
CMD ["sh", "-c", "uvicorn app.main:app --host \"$BIND_HOST\" --port 8002"]
